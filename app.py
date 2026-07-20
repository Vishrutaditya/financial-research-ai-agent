import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from services.ai_service import get_ai_market_insight
from services.calculations import add_technical_indicators, get_latest_signal
from services.news_service import get_company_news
from services.sentiment_service import analyze_sentiment
from services.stock_data import StockDataError, get_company_info, get_historical_data
from utils.helpers import format_currency, format_percentage, summarize_news_with_sentiment


@st.cache_data(ttl=300, show_spinner=False)
def cached_company_info(symbol: str) -> dict:
    return get_company_info(symbol)


@st.cache_data(ttl=300, show_spinner=False)
def cached_historical_data(symbol: str, period: str = "6mo"):
    return get_historical_data(symbol, period=period)


@st.cache_data(ttl=600, show_spinner=False)
def cached_news(company_name: str):
    return get_company_news(company_name)


st.set_page_config(page_title="Indian Stock Research Assistant", page_icon="📈", layout="wide")
st.title("Indian Stock Research Assistant")

stock_symbol = st.text_input("Enter NSE Stock Symbol", "")

if st.button("Analyze"):
    if not stock_symbol:
        st.error("Please enter a stock symbol.")
    else:
        ticker_symbol = stock_symbol.upper() + ".NS"

        try:
            company = cached_company_info(ticker_symbol)
        except StockDataError as e:
            st.error(f"❌ {e}")
        else:
            # ---------- Corporate profile ----------
            col1, col2, col3 = st.columns(3)
            col1.metric("Current Price", format_currency(company.get("current_price")))
            col2.metric("52-Week High", format_currency(company.get("fifty_two_week_high")))
            col3.metric("52-Week Low", format_currency(company.get("fifty_two_week_low")))

            col4, col5 = st.columns(2)
            col4.metric("Market Cap", format_currency(company.get("market_cap")))
            col5.metric("Dividend Yield", format_percentage(company.get("dividend_yield")))

            st.markdown("### Corporate Profile")
            st.write(f"**Company Name:** {company.get('name', stock_symbol.upper())}")
            st.write(f"**Sector:** {company.get('sector', 'N/A')}")
            st.write(f"**Industry:** {company.get('industry', 'N/A')}")
            st.write(f"**Website:** [Visit Website]({company.get('website', '#')})")

            # ---------- Technical indicators + chart ----------
            st.markdown("### Technical Snapshot")

            hist = None
            signal = {}
            sma_val = ema_val = None

            try:
                hist = cached_historical_data(ticker_symbol, period="6mo")
            except StockDataError as e:
                st.warning(f"Could not load historical prices: {e}")

            if hist is not None and not hist.empty:
                hist = add_technical_indicators(hist)
                signal = get_latest_signal(hist)
                sma_val = hist["SMA_20"].iloc[-1]
                ema_val = hist["EMA_20"].iloc[-1]

                t1, t2, t3 = st.columns(3)
                t1.metric("SMA (20)", "N/A" if pd.isna(sma_val) else f"₹{sma_val:.2f}")
                t2.metric("EMA (20)", "N/A" if pd.isna(ema_val) else f"₹{ema_val:.2f}")
                t3.metric("RSI (14)", signal.get("rsi", "N/A"), signal.get("rsi_signal", ""))

                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=hist.index, y=hist["Close"], name="Close Price",
                    line=dict(color="#00FFCC", width=2),
                ))
                fig.add_trace(go.Scatter(
                    x=hist.index, y=hist["SMA_20"], name="SMA (20)",
                    line=dict(color="#FFB347", width=1.5),
                ))
                fig.add_trace(go.Scatter(
                    x=hist.index, y=hist["EMA_20"], name="EMA (20)",
                    line=dict(color="#77B6EA", width=1.5),
                ))
                fig.update_layout(
                    title=f"{stock_symbol.upper()} 6-Month Historical Price Trend",
                    xaxis_title="Date",
                    yaxis_title="Price (INR)",
                    template="plotly_dark",
                    margin=dict(l=20, r=20, t=40, b=20),
                )
                st.plotly_chart(fig, width="stretch")
            else:
                st.warning("No historical pricing data available for this symbol.")

            # ---------- News + sentiment ----------
            st.markdown("### 📰 Latest News")

            articles = cached_news(company.get("name") or stock_symbol.upper())
            news_with_sentiment = []

            if articles:
                for article in articles:
                    title = article.get("title") or "Untitled"
                    source = (article.get("source") or {}).get("name", "Unknown source")
                    sentiment = analyze_sentiment(title)
                    news_with_sentiment.append(
                        {"title": title, "source": source, "sentiment": sentiment}
                    )

                    st.write(f"**Title:** {title}")
                    st.write(f"**Sentiment:** {sentiment}")
                    st.write(f"**Source:** {source}")
                    st.write(f"**Published:** {article.get('publishedAt', 'N/A')}")
                    st.write(f"🔗 {article.get('url', '')}")
                    st.divider()
            else:
                st.warning("No news found for this company.")

            # ---------- AI insight: fed by EVERY service above ----------
            st.markdown("### GenAI Market Insights")

            context = {
                "company_name": company.get("name", stock_symbol.upper()),
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

            with st.spinner("Consulting Gemini AI for a combined fundamental + technical + news view..."):
                ai_insight = get_ai_market_insight(context)
                st.info(ai_insight)