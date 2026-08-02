"""
app.py

Python Full-Stack Indian Stock Comparison & Fundamental Analysis Application.
Integrates NSE/BSE data (.NS/.BO), SQLite Watchlist persistence, Fundamental Ratios
(P/E, Debt/Equity, ROE, Growth), Sector Benchmarking, and Indian Market Hours (IST).
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from services.ai_service import (
    extract_stock_symbol,
    get_ai_comparison_insight,
    get_ai_followup_response,
    get_ai_market_insight,
)
from services.calculations import add_technical_indicators, get_latest_signal
from services.comparison import compare_stocks_fundamentals, get_normalized_comparison_history
from services.database_service import (
    add_to_watchlist,
    get_watchlist,
    init_db,
    is_in_watchlist,
    remove_from_watchlist,
    update_watchlist_item,
)
from services.fundamental import evaluate_fundamental_health
from services.news_service import get_company_news
from services.sector_data import get_sector_info
from services.sentiment_service import analyze_sentiment
from services.stock_data import StockDataError, get_company_info, get_historical_data
from utils.helpers import (
    format_inr_currency,
    format_percentage,
    get_indian_market_status,
    summarize_news_with_sentiment,
)

# 1. Page & Layout Setup
st.set_page_config(
    page_title="Indian Stock Comparison & Fundamentals",
    page_icon="🇮🇳",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 2. Initialize SQLite Database
init_db()


# 3. Caching Services
@st.cache_data(ttl=300, show_spinner=False)
def cached_company_info(symbol: str, exchange: str = "NSE") -> dict:
    return get_company_info(symbol, preferred_exchange=exchange)


@st.cache_data(ttl=300, show_spinner=False)
def cached_historical_data(symbol: str, period: str = "6mo", exchange: str = "NSE"):
    return get_historical_data(symbol, period=period, preferred_exchange=exchange)


@st.cache_data(ttl=600, show_spinner=False)
def cached_news(company_name: str):
    return get_company_news(company_name)


# 4. Custom Styling (Modern Dark Financial Theme)
st.markdown(
    """
    <style>
    .stApp {
        background-color: #0e1117;
        color: #e0e0e0;
    }

    /* Market Status Bar */
    .market-status-bar {
        background-color: #1a1d24;
        border: 1px solid #2e3440;
        border-radius: 12px;
        padding: 10px 18px;
        margin-bottom: 20px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }

    /* Card Containers */
    .metric-card {
        background-color: #1a1d24;
        border: 1px solid #2e3440;
        border-radius: 14px;
        padding: 16px;
        margin-bottom: 12px;
    }

    .winner-highlight {
        background-color: rgba(46, 160, 67, 0.15);
        border: 1px solid #2ea043;
        border-radius: 6px;
        padding: 2px 6px;
        color: #56d364;
        font-weight: 600;
    }

    /* Header styling */
    .main-header {
        font-size: 2.2rem;
        font-weight: 800;
        background: linear-gradient(90deg, #ff9933 0%, #ffffff 50%, #138808 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0px;
    }
    
    .sub-header {
        color: #8b949e;
        font-size: 1.05rem;
        margin-bottom: 20px;
    }

    header[data-testid="stHeader"] {
        background: transparent;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# 5. Sidebar Navigation & Global Controls
with st.sidebar:
    st.markdown("## 🇮🇳 Indian Stock Hub")
    st.caption("NSE & BSE Real-Time Financial Suite")

    # Exchange Switcher
    pref_exchange = st.radio(
        "Default Exchange",
        ["NSE (.NS)", "BSE (.BO)"],
        index=0,
        help="Select default exchange suffix when entering ticker symbols",
    )
    selected_exchange_code = "NSE" if "NSE" in pref_exchange else "BSE"

    st.markdown("---")

    # Timeframe Selector
    st.session_state.selected_period = st.selectbox(
        "Historical Period",
        ["1mo", "3mo", "6mo", "1yr", "2yr", "5yr"],
        index=2,
    )

    st.markdown("---")

    # Quick Watchlist Sidebar Section
    st.markdown("### 📋 Quick Watchlist")
    watchlist_items = get_watchlist()
    if watchlist_items:
        for item in watchlist_items[:6]:
            c1, c2 = st.columns([3, 1])
            with c1:
                if st.button(f"📈 {item['stock_symbol']}", key=f"sb_wl_{item['id']}"):
                    st.session_state.search_input = item["stock_symbol"]
                    st.rerun()
            with c2:
                if st.button("🗑️", key=f"sb_del_{item['id']}"):
                    remove_from_watchlist(item["stock_symbol"])
                    st.rerun()
    else:
        st.caption("Watchlist is currently empty.")

    st.markdown("---")
    st.markdown("#### ⚡ Popular Indian Equities")
    col_p1, col_p2 = st.columns(2)
    with col_p1:
        if st.button("RELIANCE", use_container_width=True):
            st.session_state.search_input = "RELIANCE"
            st.rerun()
        if st.button("TATAMOTORS", use_container_width=True):
            st.session_state.search_input = "TATAMOTORS"
            st.rerun()
    with col_p2:
        if st.button("TCS", use_container_width=True):
            st.session_state.search_input = "TCS"
            st.rerun()
        if st.button("HDFCBANK", use_container_width=True):
            st.session_state.search_input = "HDFCBANK"
            st.rerun()


# 6. Main Header & Indian Market Hours Status Banner
m_status = get_indian_market_status()

st.markdown('<div class="main-header">Indian Stock Comparison & Analytics</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-header">Comprehensive Fundamental Ratios, Sector Peer Benchmarking & SQLite Watchlists</div>',
    unsafe_allow_html=True,
)

# Market Hours Banner
c_st1, c_st2, c_st3 = st.columns([2, 2, 2])
with c_st1:
    st.info(f"{m_status['badge_color']} **Market Status:** {m_status['status']}")
with c_st2:
    st.info(f"🕒 **Current IST:** {m_status['current_time']}")
with c_st3:
    st.info(f"⏳ **Schedule:** {m_status['next_event']}")

st.markdown("---")


# 7. Main Multi-Tab Interface
tab_research, tab_compare, tab_sector, tab_watchlist = st.tabs(
    [
        "📊 Stock Fundamentals & Research",
        "⚖️ Multi-Stock Comparison Engine",
        "🏬 Sector Benchmark & Industry",
        "📋 Watchlist Database",
    ]
)


# ==============================================================================
# TAB 1: SINGLE STOCK FUNDAMENTALS & RESEARCH
# ==============================================================================
with tab_research:
    search_query = st.text_input(
        "Search Indian Stock Symbol (e.g. TATAMOTORS, RELIANCE, TCS, INFY, 500325.BO):",
        value=st.session_state.get("search_input", "TATAMOTORS"),
        key="main_stock_search",
    )

    if search_query:
        symbol = extract_stock_symbol(search_query) or search_query
        
        try:
            with st.spinner(f"Fetching financial data for {symbol}..."):
                company = cached_company_info(symbol, exchange=selected_exchange_code)
                health = evaluate_fundamental_health(company)
                clean_sym = company["ticker_symbol"]
                
                hist = cached_historical_data(
                    clean_sym,
                    period=st.session_state.get("selected_period", "6mo"),
                    exchange=selected_exchange_code,
                )

            # Stock Header Row with Watchlist Button
            col_h1, col_h2 = st.columns([4, 1])
            with col_h1:
                st.markdown(
                    f"## 🏢 {company['name']} ({company['symbol']}) "
                    f"`{company['exchange']}`"
                )
                st.caption(
                    f"**Sector:** {company['sector']} | "
                    f"**Industry:** {company['industry']} | "
                    f"🌐 [Company Website]({company['website']})"
                )
            with col_h2:
                in_wl = is_in_watchlist(clean_sym)
                if in_wl:
                    if st.button("⭐ Saved in Watchlist", key="btn_wl_toggle", type="secondary"):
                        remove_from_watchlist(clean_sym)
                        st.success(f"Removed {clean_sym} from Watchlist!")
                        st.rerun()
                else:
                    if st.button("☆ Add to Watchlist", key="btn_wl_toggle", type="primary"):
                        add_to_watchlist(
                            company_name=company["name"],
                            stock_symbol=clean_sym,
                            exchange=company["exchange"],
                            sector=company["sector"],
                            added_price=company["current_price"],
                        )
                        st.success(f"Added {clean_sym} to SQLite Watchlist!")
                        st.rerun()

            st.markdown("---")

            # Fundamental Summary Metrics Cards
            m1, m2, m3, m4, m5 = st.columns(5)
            m1.metric("Current Price", format_inr_currency(company["current_price"]))
            m2.metric("Market Cap", format_inr_currency(company["market_cap"], is_market_cap=True))
            m3.metric("Trailing P/E", f"{company['pe_ratio']:.2f}" if company['pe_ratio'] else "N/A")
            m4.metric("Debt to Equity", f"{company['debt_to_equity']:.2f}" if company['debt_to_equity'] is not None else "N/A")
            m5.metric("ROE", format_percentage(company["roe"]))

            # Fundamental Health Scorecard Banner
            st.markdown("### 🛡️ Fundamental Health Scorecard")
            sc_col1, sc_col2 = st.columns([1, 2])
            with sc_col1:
                st.markdown(
                    f"""
                    <div class="metric-card" style="text-align:center;">
                        <h4 style="margin:0;">Health Rating</h4>
                        <h1 style="margin:10px 0; font-size:2.8rem;">{health['rating_color']} {health['score']}/100</h1>
                        <p style="margin:0; font-weight:bold;">{health['rating']}</p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            with sc_col2:
                st.markdown("##### Key Ratio Health Badges:")
                st.write(f"- **Debt Level:** {health['de_badge'][0]}")
                st.write(f"- **Valuation (P/E):** {health['pe_badge'][0]}")
                st.write(f"- **Profitability (ROE):** {health['roe_badge'][0]}")
                st.write(f"- **Revenue Growth:** {health['growth_badge'][0]}")

            st.markdown("---")

            # Fundamental Ratios Deep-Dive Grid
            st.markdown("### 📐 Comprehensive Fundamental Analysis")
            f_col1, f_col2, f_col3 = st.columns(3)

            with f_col1:
                st.markdown("#### 💎 Valuation Metrics")
                st.write(f"• **Trailing P/E:** {company['pe_ratio'] or 'N/A'}")
                st.write(f"• **Forward P/E:** {company['forward_pe'] or 'N/A'}")
                st.write(f"• **Price to Book (P/B):** {company['pb_ratio'] or 'N/A'}")
                st.write(f"• **PEG Ratio:** {company['peg_ratio'] or 'N/A'}")
                st.write(f"• **EV / EBITDA:** {company['ev_to_ebitda'] or 'N/A'}")
                st.write(f"• **Dividend Yield:** {format_percentage(company['dividend_yield'])}")

            with f_col2:
                st.markdown("#### 🏥 Debt & Balance Sheet")
                st.write(f"• **Debt to Equity:** {company['debt_to_equity'] if company['debt_to_equity'] is not None else 'N/A'}")
                st.write(f"• **Current Ratio:** {company['current_ratio'] or 'N/A'}")
                st.write(f"• **Quick Ratio:** {company['quick_ratio'] or 'N/A'}")
                st.write(f"• **Total Debt:** {format_inr_currency(company['total_debt'], is_market_cap=True)}")
                st.write(f"• **Total Cash:** {format_inr_currency(company['total_cash'], is_market_cap=True)}")
                st.write(f"• **Book Value / Share:** ₹{company['book_value'] or 'N/A'}")

            with f_col3:
                st.markdown("#### 📈 Growth & Profitability")
                st.write(f"• **Return on Equity (ROE):** {format_percentage(company['roe'])}")
                st.write(f"• **Return on Assets (ROA):** {format_percentage(company['roa'])}")
                st.write(f"• **Revenue Growth (YoY):** {format_percentage(company['revenue_growth'])}")
                st.write(f"• **Earnings Growth (YoY):** {format_percentage(company['earnings_growth'])}")
                st.write(f"• **Operating Margin:** {format_percentage(company['operating_margin'])}")
                st.write(f"• **Net Profit Margin:** {format_percentage(company['profit_margin'])}")

            st.markdown("---")

            # Technical Trend & Plotly Price Chart
            st.markdown("### 📈 Price Performance & Technical Indicators")
            if hist is not None and not hist.empty:
                hist = add_technical_indicators(hist)
                signal = get_latest_signal(hist)

                t1, t2, t3 = st.columns(3)
                sma_v = hist['SMA_20'].iloc[-1]
                ema_v = hist['EMA_20'].iloc[-1]
                t1.metric("SMA (20)", f"₹{sma_v:.2f}" if pd.notna(sma_v) else "N/A")
                t2.metric("EMA (20)", f"₹{ema_v:.2f}" if pd.notna(ema_v) else "N/A")
                t3.metric("RSI (14)", signal.get("rsi", "N/A"), delta=signal.get("rsi_signal", ""))

                # Plotly Price Chart
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
                            name="SMA 20",
                            line=dict(color="#FFB347", width=1.5, dash="dash"),
                        )
                    )
                if "EMA_20" in hist.columns:
                    fig.add_trace(
                        go.Scatter(
                            x=hist.index,
                            y=hist["EMA_20"],
                            name="EMA 20",
                            line=dict(color="#9B72CB", width=1.5, dash="dot"),
                        )
                    )

                fig.update_layout(
                    title=f"{company['symbol']} Price History (INR)",
                    xaxis_title="Date",
                    yaxis_title="Price (₹)",
                    template="plotly_dark",
                    height=380,
                    margin=dict(l=20, r=20, t=40, b=20),
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                )
                st.plotly_chart(fig, use_container_width=True)

            st.markdown("---")

            # Gemini AI Strategic Analysis Callout
            st.markdown("### ✨ Gemini Financial Analyst Insights")
            context = {
                "company_name": company["name"],
                "sector": company["sector"],
                "industry": company["industry"],
                "current_price": company["current_price"],
                "market_cap": company["market_cap"],
                "dividend_yield": company["dividend_yield"],
                "news_summary": "Latest market information",
            }
            ai_insight = get_ai_market_insight(context)
            st.info(ai_insight)

        except StockDataError as e:
            st.error(f"❌ Could not retrieve stock details: {e}")


# ==============================================================================
# TAB 2: MULTI-STOCK COMPARISON ENGINE
# ==============================================================================
with tab_compare:
    st.markdown("### ⚖️ Side-by-Side Stock Comparison Engine")
    st.caption("Compare fundamentals, debt ratios, valuation metrics, and price growth across up to 5 Indian stocks.")

    c_top1, c_top2 = st.columns([3, 1])
    with c_top1:
        comp_input = st.text_input(
            "Enter stock symbols separated by comma (e.g., RELIANCE, TCS, INFY, TATAMOTORS, MARUTI):",
            value="TATAMOTORS, MARUTI, M&M",
            key="comp_symbols_input",
        )
    with c_top2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("📋 Compare Saved Watchlist", use_container_width=True, type="secondary"):
            wl = get_watchlist()
            if wl:
                comp_input = ", ".join([w["stock_symbol"] for w in wl[:5]])
                st.session_state.comp_symbols_input = comp_input
                st.rerun()
            else:
                st.warning("Watchlist is currently empty.")

    if comp_input:
        raw_symbols = [s.strip() for s in comp_input.split(",") if s.strip()]
        
        if len(raw_symbols) < 2:
            st.warning("Please enter at least 2 stock symbols to compare.")
        else:
            with st.spinner("Fetching comparison data across Indian markets..."):
                stock_data_list, winners = compare_stocks_fundamentals(
                    raw_symbols, preferred_exchange=selected_exchange_code
                )

            if stock_data_list:
                # 1. Comparative Metrics Matrix Table
                st.markdown("#### 📊 Comparative Fundamental Metrics Matrix")
                
                rows = []
                for s in stock_data_list:
                    sym = s["symbol"]

                    def win_mark(metric_key, formatted_val):
                        if winners.get(metric_key) == sym:
                            return f"🏆 {formatted_val}"
                        return str(formatted_val)

                    rows.append(
                        {
                            "Stock / Ticker": f"{s['name']} ({sym})",
                            "Exchange": s["exchange"],
                            "Price (₹)": format_inr_currency(s["current_price"]),
                            "Market Cap": format_inr_currency(s["market_cap"], is_market_cap=True),
                            "Health Score": win_mark("health_score", f"{s['health']['score']}/100"),
                            "P/E Ratio": win_mark("pe_ratio", f"{s['pe_ratio']:.2f}" if s['pe_ratio'] else "N/A"),
                            "Debt / Equity": win_mark("debt_to_equity", f"{s['debt_to_equity']:.2f}" if s['debt_to_equity'] is not None else "N/A"),
                            "ROE": win_mark("roe", format_percentage(s["roe"])),
                            "Rev Growth": win_mark("revenue_growth", format_percentage(s["revenue_growth"])),
                            "Div Yield": win_mark("dividend_yield", format_percentage(s["dividend_yield"])),
                        }
                    )

                df_matrix = pd.DataFrame(rows)
                st.dataframe(df_matrix, use_container_width=True, hide_index=True)

                st.markdown("---")

                # 2. Normalized Performance Overlay Chart
                st.markdown("#### 📈 Normalized % Price Performance Comparison")
                st.caption("Normalized to 0% base at start of period for direct growth comparison.")

                norm_df = get_normalized_comparison_history(
                    [s["ticker_symbol"] for s in stock_data_list],
                    period=st.session_state.get("selected_period", "6mo"),
                    preferred_exchange=selected_exchange_code,
                )

                if not norm_df.empty:
                    fig_norm = go.Figure()
                    for col in norm_df.columns:
                        fig_norm.add_trace(
                            go.Scatter(
                                x=norm_df.index,
                                y=norm_df[col],
                                name=col,
                                mode="lines",
                                line=dict(width=2.5),
                            )
                        )
                    fig_norm.update_layout(
                        title=f"Relative Performance Comparison (% Return)",
                        xaxis_title="Date",
                        yaxis_title="Percentage Change (%)",
                        template="plotly_dark",
                        height=420,
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)",
                    )
                    st.plotly_chart(fig_norm, use_container_width=True)

                st.markdown("---")

                # 3. Bar Chart Comparison of Fundamental Ratios
                st.markdown("#### 📊 Comparative Fundamental Ratios Breakdown")
                
                chart_symbols = [s["symbol"] for s in stock_data_list]
                chart_pe = [s.get("pe_ratio") or 0 for s in stock_data_list]
                chart_de = [s.get("debt_to_equity") or 0 for s in stock_data_list]
                chart_roe = [(s.get("roe") or 0) * 100 for s in stock_data_list]

                bc1, bc2 = st.columns(2)
                with bc1:
                    fig_pe = go.Figure(
                        data=[go.Bar(x=chart_symbols, y=chart_pe, marker_color="#4285F4")]
                    )
                    fig_pe.update_layout(
                        title="Trailing P/E Ratio (Lower = Cheaper)",
                        template="plotly_dark",
                        height=300,
                    )
                    st.plotly_chart(fig_pe, use_container_width=True)

                with bc2:
                    fig_de = go.Figure(
                        data=[go.Bar(x=chart_symbols, y=chart_de, marker_color="#EA4335")]
                    )
                    fig_de.update_layout(
                        title="Debt to Equity Ratio (Lower = Safer)",
                        template="plotly_dark",
                        height=300,
                    )
                    st.plotly_chart(fig_de, use_container_width=True)

                st.markdown("---")

                # 4. AI Comparative Verdict
                st.markdown("### ✨ Gemini AI Comparative Synthesis")
                ai_comp_insight = get_ai_comparison_insight(stock_data_list)
                st.info(ai_comp_insight)


# ==============================================================================
# TAB 3: SECTOR BENCHMARK & INDUSTRY
# ==============================================================================
with tab_sector:
    st.markdown("### 🏬 Indian Market Sector Benchmarks")
    st.caption("Compare stock performance against Indian Industry Sectors and Sector Peers.")

    sector_choice = st.selectbox(
        "Select Indian Industry Sector:",
        [
            "Technology",
            "Financial Services",
            "Automobile",
            "Energy",
            "Consumer Goods",
            "Healthcare",
            "Basic Materials",
        ],
    )

    sec_info = get_sector_info(sector_choice)
    st.markdown(f"#### 🎯 Sector Benchmark Index: `{sec_info['index_name']}` ({sec_info['index_symbol']})")

    st.markdown("##### Key Sector Peer Equities:")
    peer_symbols = [p["symbol"] for p in sec_info["peers"]]

    with st.spinner("Fetching sector peer fundamentals..."):
        peer_data_list, peer_winners = compare_stocks_fundamentals(peer_symbols)

    if peer_data_list:
        peer_rows = []
        for p in peer_data_list:
            peer_rows.append(
                {
                    "Peer Company": p["name"],
                    "Ticker": p["symbol"],
                    "Current Price": format_inr_currency(p["current_price"]),
                    "Market Cap": format_inr_currency(p["market_cap"], is_market_cap=True),
                    "Health Score": f"{p['health']['score']}/100",
                    "P/E Ratio": f"{p['pe_ratio']:.2f}" if p['pe_ratio'] else "N/A",
                    "Debt / Equity": f"{p['debt_to_equity']:.2f}" if p['debt_to_equity'] is not None else "N/A",
                    "ROE": format_percentage(p["roe"]),
                }
            )
        st.dataframe(pd.DataFrame(peer_rows), use_container_width=True, hide_index=True)


# ==============================================================================
# TAB 4: WATCHLIST DATABASE
# ==============================================================================
with tab_watchlist:
    st.markdown("### 📋 SQLite Saved Watchlists")
    st.caption("Persistent local SQLite database storing your tracked Indian equities and price logs.")

    wl_data = get_watchlist()

    if not wl_data:
        st.info("No stocks saved in your SQLite watchlist yet. Search for a stock in Tab 1 and click 'Add to Watchlist'!")
    else:
        # Table View of Saved Items
        st.markdown("#### Saved Equities Portfolio Track:")
        
        wl_table_rows = []
        for item in wl_data:
            wl_table_rows.append(
                {
                    "ID": item["id"],
                    "Symbol": item["stock_symbol"],
                    "Company Name": item["company_name"],
                    "Exchange": item["exchange"],
                    "Sector": item["sector"],
                    "Price Added": format_inr_currency(item["added_price"]),
                    "Added On": item["created_at"],
                }
            )

        st.dataframe(pd.DataFrame(wl_table_rows), use_container_width=True, hide_index=True)

        st.markdown("---")

        st.markdown("#### Manage Watchlist Items:")
        for item in wl_data:
            wc1, wc2, wc3 = st.columns([3, 2, 1])
            with wc1:
                st.write(f"**{item['company_name']}** ({item['stock_symbol']})")
            with wc2:
                notes_val = st.text_input(
                    "Target / Notes:",
                    value=item.get("notes") or "",
                    key=f"note_in_{item['id']}",
                    label_visibility="collapsed",
                    placeholder="Add target price or personal note...",
                )
                if st.button("Save Note", key=f"btn_note_save_{item['id']}"):
                    update_watchlist_item(item["stock_symbol"], notes=notes_val)
                    st.success("Updated note!")
                    st.rerun()
            with wc3:
                if st.button("🗑️ Remove", key=f"wl_page_del_{item['id']}", type="secondary"):
                    remove_from_watchlist(item["stock_symbol"])
                    st.success(f"Removed {item['stock_symbol']}!")
                    st.rerun()
