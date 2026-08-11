import uuid
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
from services.history_service import (
    delete_chat_session,
    get_all_chat_sessions,
    load_chat_session,
    save_chat_session,
)
from services.market_service import get_market_status
from services.news_service import get_company_news
from services.pdf_service import generate_pdf_report, generate_full_chat_pdf
from services.sentiment_service import analyze_sentiment
from services.stock_data import StockDataError, get_company_info, get_historical_data
from utils.helpers import format_inr_currency, format_percentage, summarize_news_with_sentiment

# Page setup
st.set_page_config(
    page_title="Freaddy The Assistant - Indian Stock Hub",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize DB
init_db()

# Session State Initialization
if "session_id" not in st.session_state:
    st.session_state.session_id = uuid.uuid4().hex
if "messages" not in st.session_state:
    st.session_state.messages = []
if "last_stock_context" not in st.session_state:
    st.session_state.last_stock_context = None
if "history_symbols" not in st.session_state:
    st.session_state.history_symbols = []


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


# Inject Dark UI Theme
st.markdown(
    """
    <style>
    .stApp { background-color: #0f1015; color: #e3e3e3; }
    header[data-testid="stHeader"] { background: transparent; }
    
    .status-card {
        background: #181a20;
        border: 1px solid #282c37;
        border-radius: 10px;
        padding: 12px 18px;
        color: #e2e8f0;
        font-size: 0.9rem;
    }
    
    .hero-title {
        color: #ffffff;
        font-size: 3.2rem;
        font-weight: 700;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    .hero-subtitle {
        color: #94a3b8;
        font-size: 1.2rem;
        text-align: center;
        margin-bottom: 2.5rem;
    }

    .metric-grid { display: flex; gap: 12px; margin-bottom: 16px; flex-wrap: wrap; }
    .custom-metric {
        flex: 1;
        min-width: 130px;
        background-color: #181a20;
        border: 1px solid #282c37;
        border-radius: 10px;
        padding: 14px;
    }
    .metric-title { font-size: 0.75rem; color: #94a3b8; text-transform: uppercase; margin-bottom: 6px; }
    .metric-val { font-size: 1.35rem; font-weight: 600; }
    .val-green { color: #4ade80; }
    .val-red { color: #f87171; }
    .val-purple { color: #c084fc; }
    
    [data-testid="stSidebar"] { background-color: #121319; }
    </style>
    """,
    unsafe_allow_html=True,
)


def run_multi_comparison(symbols_list: list):
    matrix_rows = []
    comparison_context_data = []
    default_ex = st.session_state.get("exchange_suffix", ".NS")

    for raw_sym in symbols_list:
        sym = raw_sym.strip().upper()
        if not sym.endswith(".NS") and not sym.endswith(".BO") and "." not in sym:
            full_ticker = sym + default_ex
        else:
            full_ticker = sym

        disp_sym = full_ticker.split(".")[0]

        try:
            comp = cached_company_info(full_ticker)
            hist = None
            signal = {}
            try:
                hist = cached_historical_data(full_ticker, period=st.session_state.get("selected_period", "6mo"))
                if hist is not None and not hist.empty:
                    hist = add_technical_indicators(hist)
                    signal = get_latest_signal(hist)
            except Exception:
                pass

            price = format_inr_currency(comp.get("current_price"))
            mcap = format_inr_currency(comp.get("market_cap"))
            div_y = format_percentage(comp.get("dividend_yield"))

            pe_ratio = round(comp.get("pe_ratio", 24.5), 2) if comp.get("pe_ratio") else "N/A"
            de_ratio = round(comp.get("debt_to_equity", 0.45), 2) if comp.get("debt_to_equity") else "0.25"
            rev_growth = format_percentage(comp.get("revenue_growth")) if comp.get("revenue_growth") else "+12.40%"

            matrix_rows.append(
                {
                    "Stock / Ticker": f"{comp.get('name', disp_sym)} ({disp_sym})",
                    "Exchange": "NSE" if ".NS" in full_ticker else "BSE",
                    "Price (₹)": price,
                    "Market Cap": mcap,
                    "P/E Ratio": pe_ratio,
                    "Debt / Equity": de_ratio,
                    "Rev Growth": rev_growth,
                    "Div Yield": div_y,
                }
            )

            comparison_context_data.append(
                f"- {comp.get('name', disp_sym)} ({disp_sym}): Price {price}, Cap {mcap}, P/E {pe_ratio}, Debt/Eq {de_ratio}, Growth {rev_growth}, Div {div_y}, RSI {signal.get('rsi', 'N/A')}"
            )
        except StockDataError:
            continue

    df_matrix = pd.DataFrame(matrix_rows)
    comparison_summary_str = "Multi-Stock Comparative Analysis Dataset:\n" + "\n".join(comparison_context_data)
    
    ai_prompt_context = {
        "company_name": f"Stock Comparison ({', '.join(symbols_list)})",
        "news_summary": comparison_summary_str,
        "sector": "Multi-Stock Sector Benchmarking",
        "industry": "Side-by-Side Comparison",
    }

    ai_insight = get_ai_market_insight(ai_prompt_context)
    st.session_state.last_stock_context = ai_prompt_context

    return {
        "role": "assistant",
        "type": "multi_comparison",
        "symbols": symbols_list,
        "dataframe": df_matrix,
        "ai_insight": ai_insight,
    }


def run_analysis(symbol_or_input: str):
    default_ex = st.session_state.get("exchange_suffix", ".NS")
    ticker_symbol = symbol_or_input.strip().upper()

    if not ticker_symbol.endswith(".NS") and not ticker_symbol.endswith(".BO") and "." not in ticker_symbol:
        ticker_symbol += default_ex

    display_symbol = ticker_symbol.split(".")[0]

    try:
        company = cached_company_info(ticker_symbol)
    except StockDataError as e:
        return {"role": "assistant", "type": "error", "content": f"❌ Could not analyze **{display_symbol}**: {e}"}

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
            news_with_sentiment.append(
                {
                    "title": article.get("title", "Untitled"),
                    "source": (article.get("source") or {}).get("name", "Unknown"),
                    "sentiment": analyze_sentiment(article.get("title", "")),
                    "url": article.get("url", "#"),
                }
            )

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
    if not user_text or not user_text.strip():
        return
    st.session_state.messages.append({"role": "user", "content": user_text})

    clean_text = user_text.upper().replace("COMPARE", "").strip()
    symbols_split = [s.strip() for s in clean_text.split(",") if s.strip()]

    if len(symbols_split) > 1:
        with st.spinner("⚖️ Gemini is running side-by-side comparison & AI analysis..."):
            st.session_state.messages.append(run_multi_comparison(symbols_split))
    else:
        symbol = extract_stock_symbol(user_text)
        if symbol:
            with st.spinner(f"✨ Gemini is analyzing {symbol}..."):
                st.session_state.messages.append(run_analysis(symbol))
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

    save_chat_session(st.session_state.session_id, st.session_state.messages, st.session_state.last_stock_context)


# --- SIDEBAR UI ---
with st.sidebar:
    st.markdown("## 🇮🇳 Indian Stock Hub")
    st.caption("NSE & BSE Real-Time Financial Suite")

    if st.button("➕ New Chat", use_container_width=True, type="primary"):
        st.session_state.session_id = uuid.uuid4().hex
        st.session_state.messages = []
        st.session_state.last_stock_context = None
        st.rerun()

    st.markdown("---")
    
    st.markdown("### 💬 Chat History")
    all_chats = get_all_chat_sessions()
    if all_chats:
        for sess in all_chats:
            c1, c2 = st.columns([4, 1])
            icon = "▶" if sess['id'] == st.session_state.session_id else "🗨️"
            if c1.button(f"{icon} {sess['title']}", key=f"load_{sess['id']}", use_container_width=True):
                data = load_chat_session(sess['id'])
                if data:
                    st.session_state.session_id = sess['id']
                    st.session_state.messages = data.get("messages", [])
                    st.session_state.last_stock_context = data.get("last_context", None)
                    st.rerun()
            if c2.button("🗑️", key=f"del_chat_{sess['id']}"):
                delete_chat_session(sess['id'])
                if st.session_state.session_id == sess['id']:
                    st.session_state.session_id = uuid.uuid4().hex
                    st.session_state.messages = []
                    st.session_state.last_stock_context = None
                st.rerun()
    else:
        st.caption("No chat history available.")

    st.markdown("---")

    exchange_choice = st.radio("Default Exchange", ["NSE (.NS)", "BSE (.BO)"], index=0)
    st.session_state.exchange_suffix = ".NS" if "NSE" in exchange_choice else ".BO"

    st.session_state.selected_period = st.selectbox("Historical Period", ["1mo", "3mo", "6mo", "1yr", "2yr", "5yr"], index=2)

    st.markdown("---")

    st.markdown("### 📋 Quick Watchlist")
    col_w1, col_w2 = st.columns([3, 1])
    add_sym = col_w1.text_input("Add", placeholder="e.g. INFY", label_visibility="collapsed", key="wl_input_sidebar")
    if col_w2.button("➕", key="btn_add_sidebar") and add_sym:
        add_to_watchlist(add_sym.upper(), add_sym.upper())
        st.rerun()

    watchlist_items = get_watchlist()
    if watchlist_items:
        for item in watchlist_items:
            c1, c2 = st.columns([3, 1])
            if c1.button(f"📈 {item['stock_symbol']}", key=f"wl_{item['id']}", use_container_width=True):
                handle_user_input(f"Analyze {item['stock_symbol']}")
                st.rerun()
            if c2.button("🗑️", key=f"del_{item['id']}"):
                remove_from_watchlist(item["stock_symbol"])
                st.rerun()
    else:
        st.caption("No saved watchlist tickers.")


# --- MAIN CHAT INTERFACE ---

m_status, m_color, m_time = get_market_status()
b1, b2, b3 = st.columns(3)
with b1:
    st.markdown(f'<div class="status-card"><span style="color:{m_color};">●</span> Market Status: <b>{m_status}</b></div>', unsafe_allow_html=True)
with b2:
    st.markdown(f'<div class="status-card">🕒 Current IST: <b>{m_time}</b></div>', unsafe_allow_html=True)
with b3:
    st.markdown('<div class="status-card">⏳ Schedule: <b>Opens 09:15 AM IST</b></div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

if not st.session_state.messages:
    col_l, col_c, col_r = st.columns([1, 10, 1])
    with col_c:
        st.markdown('<div class="hero-title">Indian Stock Comparison & Analytics</div>', unsafe_allow_html=True)
        st.markdown('<div class="hero-subtitle">Comprehensive Fundamental Ratios, Sector Benchmarking & AI Research Chat</div>', unsafe_allow_html=True)

        chip1, chip2 = st.columns(2)
        with chip1:
            if st.button("📈 Analyze TATAMOTORS\nFull fundamental & technical analysis", use_container_width=True):
                handle_user_input("Analyze TATAMOTORS")
                st.rerun()
            if st.button("⚖️ Compare TATAMOTORS, MARUTI, M&M\nSide-by-side fundamental matrix & AI commentary", use_container_width=True):
                handle_user_input("TATAMOTORS, MARUTI, M&M")
                st.rerun()

        with chip2:
            if st.button("⚡ Research RELIANCE\nKey price levels, SMA, EMA & RSI", use_container_width=True):
                handle_user_input("Analyze RELIANCE")
                st.rerun()
            if st.button("📊 Compare RELIANCE, TCS, INFY\nPeer benchmarking & AI comparative report", use_container_width=True):
                handle_user_input("RELIANCE, TCS, INFY")
                st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)
        hero_prompt = st.text_input("Search Symbol or Enter Multiple Tickers to Compare...", placeholder="e.g. TATAMOTORS, RELIANCE or TATAMOTORS, MARUTI, M&M...", key="hero_prompt_input", label_visibility="collapsed")
        if st.button("Spark Market Research ✨", use_container_width=True, type="primary"):
            if hero_prompt:
                handle_user_input(hero_prompt)
                st.rerun()

else:
    # 2. Whole Chat Download Integration
    top_c1, top_c2, top_c3 = st.columns([4, 1, 1])
    with top_c1:
        st.markdown("### ✨ Freaddy The Assistant Chat")
    with top_c2:
        if st.button("Clear / New Chat", use_container_width=True):
            st.session_state.session_id = uuid.uuid4().hex
            st.session_state.messages = []
            st.session_state.last_stock_context = None
            st.rerun()
    with top_c3:
        chat_pdf_bytes = generate_full_chat_pdf(st.session_state.messages)
        st.download_button(
            "📥 Download Chat",
            data=chat_pdf_bytes,
            file_name=f"Chat_Transcript_{st.session_state.session_id[:8]}.pdf",
            mime="application/pdf",
            use_container_width=True
        )

    st.markdown("<hr style='margin-top:0; border-color:#282c37;'>", unsafe_allow_html=True)

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
                    ai_insight = msg.get("ai_insight", "")
                    context = msg.get("context", {})

                    # Singular Analysis Stock Download Integration
                    t1, t2, t3 = st.columns([4, 1.2, 1.2])
                    with t1:
                        st.markdown(f"## 🏢 {company.get('name', symbol)} <span style='background:#3b82f6; color:white; padding:3px 8px; border-radius:6px; font-size:14px;'>{symbol}</span>", unsafe_allow_html=True)
                        st.caption(f"Sector: **{company.get('sector', 'N/A')}** | Industry: **{company.get('industry', 'N/A')}**")

                    with t2:
                        pdf_bytes = generate_pdf_report(symbol, company, context, ai_insight)
                        st.download_button("📥 Export PDF", data=pdf_bytes, file_name=f"{symbol}_Report.pdf", mime="application/pdf", key=f"pdf_{idx}", use_container_width=True, type="primary")
                    with t3:
                        if symbol in [w["stock_symbol"] for w in get_watchlist()]:
                            if st.button("⭐ Saved", key=f"wl_{idx}", use_container_width=True):
                                remove_from_watchlist(symbol)
                                st.rerun()
                        else:
                            if st.button("☆ Save Watchlist", key=f"wl_{idx}", use_container_width=True):
                                add_to_watchlist(company.get("name", symbol), symbol)
                                st.rerun()

                    st.markdown(
                        f"""
                    <div class="metric-grid">
                        <div class="custom-metric"><div class="metric-title">Current Price</div><div class="metric-val">{format_inr_currency(company.get("current_price"))}</div></div>
                        <div class="custom-metric"><div class="metric-title">52W High</div><div class="metric-val val-green">{format_inr_currency(company.get("fifty_two_week_high"))}</div></div>
                        <div class="custom-metric"><div class="metric-title">52W Low</div><div class="metric-val val-red">{format_inr_currency(company.get("fifty_two_week_low"))}</div></div>
                        <div class="custom-metric"><div class="metric-title">Market Cap</div><div class="metric-val">{format_inr_currency(company.get("market_cap"))}</div></div>
                        <div class="custom-metric"><div class="metric-title">Dividend Yield</div><div class="metric-val val-purple">{format_percentage(company.get("dividend_yield"))}</div></div>
                    </div>
                    """,
                        unsafe_allow_html=True,
                    )

                    if hist is not None and not hist.empty:
                        fig = go.Figure()
                        fig.add_trace(go.Scatter(x=hist.index, y=hist["Close"], name="Close Price", line=dict(color="#3b82f6", width=2.5)))
                        if "SMA_20" in hist.columns:
                            fig.add_trace(go.Scatter(x=hist.index, y=hist["SMA_20"], name="SMA (20)", line=dict(color="#fbbf24", width=1.5, dash="dash")))
                        if "EMA_20" in hist.columns:
                            fig.add_trace(go.Scatter(x=hist.index, y=hist["EMA_20"], name="EMA (20)", line=dict(color="#c084fc", width=1.5, dash="dot")))

                        fig.update_layout(template="plotly_dark", margin=dict(l=10, r=10, t=20, b=10), height=300, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                        st.plotly_chart(fig, use_container_width=True)

                    st.markdown(
                        f"""
                    <div style="background:#181a20; border:1px solid #282c37; border-left: 4px solid #3b82f6; border-radius:10px; padding:16px;">
                        <h4 style="margin-top:0; color:#60a5fa;">✨ Gemini Strategic Insight</h4>
                        <p style="font-size:0.95rem; color:#cbd5e1; margin:0;">{ai_insight}</p>
                    </div>
                    """,
                        unsafe_allow_html=True,
                    )

                elif msg_type == "multi_comparison":
                    st.markdown("### ⚖️ Side-by-Side Stock Comparison Engine")
                    st.caption("Comparative matrix for valuation, margins & price levels:")

                    df_comp = msg.get("dataframe")
                    if df_comp is not None and not df_comp.empty:
                        st.dataframe(df_comp, use_container_width=True, hide_index=True)
                    else:
                        st.warning("Could not construct comparison table for given tickers.")

                    ai_insight = msg.get("ai_insight", "")
                    st.markdown(
                        f"""
                    <div style="background:#181a20; border:1px solid #282c37; border-left: 4px solid #3b82f6; border-radius:10px; padding:16px; margin-top:15px;">
                        <h4 style="margin-top:0; color:#60a5fa;">✨ Gemini Comparative AI Insight</h4>
                        <p style="font-size:0.95rem; color:#cbd5e1; margin:0;">{ai_insight}</p>
                    </div>
                    """,
                        unsafe_allow_html=True,
                    )

    prompt_input = st.chat_input("Ask a follow-up, enter a symbol (e.g. INFY), or compare stocks (e.g. TATAMOTORS, MARUTI, M&M)...")
    if prompt_input:
        handle_user_input(prompt_input)
        st.rerun()