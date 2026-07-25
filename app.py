import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from services.ai_service import (
    extract_stock_symbol,
    get_ai_followup_response,
    get_ai_market_insight,
)
from services.calculations import add_technical_indicators, get_latest_signal
from services.database_service import (
    add_to_watchlist,
    get_watchlist,
    init_db,
    remove_from_watchlist,
)
from services.news_service import get_company_news
from services.sentiment_service import analyze_sentiment
from services.stock_data import StockDataError, get_company_info, get_historical_data
from utils.helpers import format_currency, format_percentage, summarize_news_with_sentiment

# Page setup
st.set_page_config(
    page_title="Gemini Financial Assistant",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize DB
init_db()

# Caching wrappers
@st.cache_data(ttl=300, show_spinner=False)
def cached_company_info(symbol: str) -> dict:
    return get_company_info(symbol)


@st.cache_data(ttl=300, show_spinner=False)
def cached_historical_data(symbol: str, period: str = "6mo"):
    return get_historical_data(symbol, period=period)


@st.cache_data(ttl=600, show_spinner=False)
def cached_news(company_name: str):
    return get_company_news(company_name)


# Session state initialization
if "messages" not in st.session_state:
    st.session_state.messages = []

if "last_stock_context" not in st.session_state:
    st.session_state.last_stock_context = None

if "history_symbols" not in st.session_state:
    st.session_state.history_symbols = []

# Inject Gemini AI modern Dark CSS
st.markdown(
    """
    <style>
    /* Dark Gemini Theme */
    .stApp {
        background-color: #131314;
        color: #e3e3e3;
    }
    
    /* Gemini Header Styling */
    .gemini-title {
        background: linear-gradient(90deg, #4285F4 0%, #9B72CB 40%, #D96570 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.8rem;
        font-weight: 700;
        margin-bottom: 0.3rem;
        letter-spacing: -0.5px;
    }
    
    .gemini-subtitle {
        color: #9aa0a6;
        font-size: 1.25rem;
        font-weight: 400;
        margin-bottom: 2rem;
    }

    /* Cards & Containers */
    .gemini-card {
        background-color: #1e1f20;
        border: 1px solid #2e2f31;
        border-radius: 16px;
        padding: 20px;
        margin-bottom: 16px;
    }

    .user-msg-box {
        background-color: #282a2c;
        border-radius: 16px;
        padding: 14px 20px;
        color: #e3e3e3;
        margin-bottom: 16px;
        border: 1px solid #3c4043;
        font-size: 1.05rem;
    }

    .ai-insight-card {
        background: linear-gradient(135deg, rgba(66, 133, 244, 0.08) 0%, rgba(155, 114, 203, 0.08) 100%);
        border-left: 4px solid #4285f4;
        border-radius: 12px;
        padding: 18px 22px;
        margin-top: 15px;
    }

    /* Hide standard header decoration */
    header[data-testid="stHeader"] {
        background: transparent;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def run_analysis(symbol_or_input: str):
    """Processes a stock symbol query and returns a structured message object."""
    ticker_symbol = symbol_or_input.strip().upper()
    if not ticker_symbol.endswith(".NS") and not "." in ticker_symbol:
        ticker_symbol += ".NS"

    display_symbol = ticker_symbol.replace(".NS", "")

    try:
        company = cached_company_info(ticker_symbol)
    except StockDataError as e:
        return {
            "role": "assistant",
            "type": "error",
            "content": f"❌ Could not analyze **{display_symbol}**: {e}",
        }

    # Fetch indicators & news
    hist = None
    signal = {}
    sma_val = ema_val = None

    period = st.session_state.get("selected_period", "6mo")

    try:
        hist = cached_historical_data(ticker_symbol, period=period)
    except StockDataError:
        pass

    if hist is not None and not hist.empty:
        hist = add_technical_indicators(hist)
        signal = get_latest_signal(hist)
        sma_val = hist["SMA_20"].iloc[-1]
        ema_val = hist["EMA_20"].iloc[-1]

    articles = cached_news(company.get("name") or display_symbol)
    news_with_sentiment = []
    if articles:
        for article in articles:
            title = article.get("title") or "Untitled"
            source = (article.get("source") or {}).get("name", "Unknown source")
            sentiment = analyze_sentiment(title)
            news_with_sentiment.append(
                {
                    "title": title,
                    "source": source,
                    "sentiment": sentiment,
                    "published": article.get("publishedAt", "N/A"),
                    "url": article.get("url", "#"),
                }
            )

    # Build context for Gemini AI
    context = {
        "company_name": company.get("name", display_symbol),
        "sector": company.get("sector"),
        "industry": company.get("industry"),
        "current_price": company.get("current_price"),
        "market_cap": company.get("market_cap"),
        "fifty_two_week_high": company.get("fifty_two_week_high"),
        "fifty_two_week_low": company.get("fifty_two_week_low"),
        "dividend_yield": company.get("dividend_yield"),
        "sma": None if sma_val is None or pd.isna(sma_val) else round(float(sma_val), 2),
        "ema": None if ema_val is None or pd.isna(ema_val) else round(float(ema_val), 2),
        "rsi": signal.get("rsi"),
        "rsi_signal": signal.get("rsi_signal"),
        "news_summary": summarize_news_with_sentiment(news_with_sentiment),
    }

    st.session_state.last_stock_context = context

    if display_symbol not in st.session_state.history_symbols:
        st.session_state.history_symbols.insert(0, display_symbol)

    ai_insight = get_ai_market_insight(context)

    return {
        "role": "assistant",
        "type": "stock_analysis",
        "symbol": display_symbol,
        "ticker_symbol": ticker_symbol,
        "company": company,
        "hist": hist,
        "signal": signal,
        "sma_val": sma_val,
        "ema_val": ema_val,
        "news": news_with_sentiment,
        "ai_insight": ai_insight,
        "context": context,
    }


def handle_user_input(user_text: str):
    """Handles incoming user prompt either as stock analysis or follow-up question."""
    if not user_text or not user_text.strip():
        return

    st.session_state.messages.append({"role": "user", "content": user_text})

    symbol = extract_stock_symbol(user_text)

    if symbol:
        with st.spinner(f"✨ Gemini is analyzing {symbol}..."):
            response_msg = run_analysis(symbol)
            st.session_state.messages.append(response_msg)
    else:
        with st.spinner("✨ Gemini AI is thinking..."):
            followup_ans = get_ai_followup_response(
                user_prompt=user_text,
                chat_history=st.session_state.messages,
                last_stock_context=st.session_state.last_stock_context,
            )
            st.session_state.messages.append(
                {"role": "assistant", "type": "conversational", "content": followup_ans}
            )


# Sidebar Configuration
with st.sidebar:
    st.markdown("## ✨ Freaddy The Assiatant")

    if st.button("➕ New Chat", use_container_width=True, type="primary"):
        st.session_state.messages = []
        st.session_state.last_stock_context = None
        st.rerun()

    st.markdown("---")

    # Timeframe selector
    st.session_state.selected_period = st.selectbox(
        "Technical Trend Period",
        ["1mo", "3mo", "6mo", "1yr", "2yr", "5yr"],
        index=2,
    )

    st.markdown("### 📋 Watchlist")
    watchlist_items = get_watchlist()
    if watchlist_items:
        for item in watchlist_items:
            c1, c2 = st.columns([3, 1])
            with c1:
                if st.button(f"📈 {item['stock_symbol']}", key=f"wl_{item['id']}"):
                    handle_user_input(f"Analyze {item['stock_symbol']}")
                    st.rerun()
            with c2:
                if st.button("🗑️", key=f"del_{item['id']}"):
                    remove_from_watchlist(item["stock_symbol"])
                    st.rerun()
    else:
        st.caption("No stocks saved in watchlist yet.")

    # Recent Session Symbol History
    if st.session_state.history_symbols:
        st.markdown("### 🕒 Recent Searches")
        for sym in st.session_state.history_symbols[:5]:
            if st.button(f"🔍 {sym}", key=f"hist_{sym}"):
                handle_user_input(f"Analyze {sym}")
                st.rerun()


# MAIN APP UI LOGIC

# State 1: Full-Page Initial Welcome Hero View
if not st.session_state.messages:
    st.markdown("<br><br>", unsafe_allow_html=True)
    col_left, col_center, col_right = st.columns([1, 10, 1])

    with col_center:
        st.markdown(
            '<div class="gemini-title">Hello, Freaddy the finacial assistant here</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div class="gemini-subtitle">What Indian stock or financial research would you like to explore today?</div>',
            unsafe_allow_html=True,
        )

        st.markdown("<br>", unsafe_allow_html=True)

        # Quick Suggestion Chips Grid
        chip_col1, chip_col2 = st.columns(2)

        with chip_col1:
            if st.button(
                "📈  Analyze TATAMOTORS\nFull fundamental, technical & news insights",
                use_container_width=True,
            ):
                handle_user_input("Analyze TATAMOTORS")
                st.rerun()

            if st.button(
                "📰  Sentiment for INFY\nLatest news headlines & AI sentiment summary",
                use_container_width=True,
            ):
                handle_user_input("Analyze INFY")
                st.rerun()

        with chip_col2:
            if st.button(
                "⚡  Research RELIANCE\nKey price levels, SMA, EMA & RSI analysis",
                use_container_width=True,
            ):
                handle_user_input("Analyze RELIANCE")
                st.rerun()

            if st.button(
                "📊  Analyze TCS\nDividend yield, market cap & strategic outlook",
                use_container_width=True,
            ):
                handle_user_input("Analyze TCS")
                st.rerun()

        st.markdown("<br><br>", unsafe_allow_html=True)

        # Center Hero Input Box
        hero_input = st.text_input(
            "Enter Stock Symbol or ask Gemini AI...",
            placeholder="e.g. TATAMOTORS, RELIANCE, TCS, or ask any stock question...",
            key="hero_prompt_input",
            label_visibility="collapsed",
        )

        if st.button("Spark Market Research ✨", use_container_width=True, type="primary"):
            if hero_input:
                handle_user_input(hero_input)
                st.rerun()

# State 2: Active Chat View (Continuous Conversation)
else:
    # Top Sticky Header
    st.markdown("### ✨ Freaddy The Assiatant")
    st.markdown("---")

    # Render message stream
    for idx, msg in enumerate(st.session_state.messages):
        if msg["role"] == "user":
            st.chat_message("user").write(msg["content"])

        elif msg["role"] == "assistant":
            with st.chat_message("assistant", avatar="✨"):
                msg_type = msg.get("type", "conversational")

                if msg_type == "error":
                    st.error(msg["content"])

                elif msg_type == "conversational":
                    st.markdown(msg["content"])

                elif msg_type == "stock_analysis":
                    symbol = msg["symbol"]
                    company = msg["company"]
                    hist = msg.get("hist")
                    signal = msg.get("signal", {})
                    news = msg.get("news", [])
                    ai_insight = msg.get("ai_insight", "")

                    # Watchlist Toggle Button
                    top_c1, top_c2 = st.columns([4, 1])
                    with top_c1:
                        st.markdown(f"## 🏢 {company.get('name', symbol)} ({symbol})")
                    with top_c2:
                        current_wl = [w["stock_symbol"] for w in get_watchlist()]
                        if symbol in current_wl:
                            if st.button("⭐ Saved", key=f"wl_btn_{idx}"):
                                remove_from_watchlist(symbol)
                                st.rerun()
                        else:
                            if st.button("☆ Add Watchlist", key=f"wl_btn_{idx}"):
                                add_to_watchlist(company.get("name", symbol), symbol)
                                st.rerun()

                    # Corporate Profile Metrics
                    m1, m2, m3, m4, m5 = st.columns(5)
                    m1.metric("Current Price", format_currency(company.get("current_price")))
                    m2.metric("52W High", format_currency(company.get("fifty_two_week_high")))
                    m3.metric("52W Low", format_currency(company.get("fifty_two_week_low")))
                    m4.metric("Market Cap", format_currency(company.get("market_cap")))
                    m5.metric("Dividend Yield", format_percentage(company.get("dividend_yield")))

                    st.markdown(
                        f"**Sector:** `{company.get('sector', 'N/A')}` | "
                        f"**Industry:** `{company.get('industry', 'N/A')}` | "
                        f"🔗 [Company Website]({company.get('website', '#')})"
                    )

                    st.markdown("---")

                    # Technical Indicators & Plotly Chart
                    st.markdown("### 📈 Technical Snapshot & Price Trend")
                    if hist is not None and not hist.empty:
                        sma_val = msg.get("sma_val")
                        ema_val = msg.get("ema_val")

                        t1, t2, t3 = st.columns(3)
                        t1.metric("SMA (20)", "N/A" if pd.isna(sma_val) else f"₹{sma_val:.2f}")
                        t2.metric("EMA (20)", "N/A" if pd.isna(ema_val) else f"₹{ema_val:.2f}")
                        t3.metric(
                            "RSI (14)",
                            signal.get("rsi", "N/A"),
                            delta=signal.get("rsi_signal", ""),
                        )

                        fig = go.Figure()
                        fig.add_trace(
                            go.Scatter(
                                x=hist.index,
                                y=hist["Close"],
                                name="Close Price",
                                line=dict(color="#4285F4", width=2.5),
                            )
                        )
                        if "SMA_20" in hist.columns:
                            fig.add_trace(
                                go.Scatter(
                                    x=hist.index,
                                    y=hist["SMA_20"],
                                    name="SMA (20)",
                                    line=dict(color="#FFB347", width=1.5, dash="dash"),
                                )
                            )
                        if "EMA_20" in hist.columns:
                            fig.add_trace(
                                go.Scatter(
                                    x=hist.index,
                                    y=hist["EMA_20"],
                                    name="EMA (20)",
                                    line=dict(color="#9B72CB", width=1.5, dash="dot"),
                                )
                            )

                        fig.update_layout(
                            title=f"{symbol} Historical Price Trend ({st.session_state.get('selected_period', '6mo')})",
                            xaxis_title="Date",
                            yaxis_title="Price (INR)",
                            template="plotly_dark",
                            margin=dict(l=20, r=20, t=40, b=20),
                            height=380,
                            paper_bgcolor="rgba(0,0,0,0)",
                            plot_bgcolor="rgba(0,0,0,0)",
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("No historical pricing data available.")

                    st.markdown("---")

                    # News Feed Section
                    st.markdown("### 📰 News & Sentiment Analysis")
                    if news:
                        for n in news[:3]:
                            st.write(
                                f"• **{n['title']}** "
                                f"| *{n['source']}* "
                                f"| `{n['sentiment']}` "
                                f"| [Read Article]({n['url']})"
                            )
                    else:
                        st.caption("No recent news found.")

                    # Gemini GenAI Market Insight Callout Box
                    st.markdown(
                        f"""
                        <div class="ai-insight-card">
                            <h4 style="margin-top:0; color:#4285f4;">✨ Gemini GenAI Strategic Market Insight</h4>
                            <p style="font-size: 1.05rem; line-height: 1.6;">{ai_insight}</p>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

    # Continuous Chat Input at the end of responses
    prompt_input = st.chat_input(
        "Ask Gemini follow-up questions (e.g. 'What is the RSI outlook?') or enter another symbol (e.g. TATAMOTORS)..."
    )
    if prompt_input:
        handle_user_input(prompt_input)
        st.rerun()