import streamlit as st
from services.stock_data import get_stock_info, get_historical_data, get_company_info
from services.ai_service import get_ai_market_insight
from services.news_service import get_company_news
from services.sentiment_service import analyze_sentiment

st.title("Indian Stock Research Assistant")

stock_symbol = st.text_input(
    "Enter NSE Stock Symbol",
    ""
)

if st.button("Analyze"):
    if not stock_symbol:
        st.error("please enter a stock symbol.")
    else:
        try:
            # 1. Fetch text profile and financial metric information from yfinance
            company = get_company_info(stock_symbol.upper() + ".NS")
            
            # --- VALIDATION: Check if company actually exists ---
            if not company or (company.get('sector') is None and company.get('industry') is None):
                st.error(f"❌ Could not find a valid company profile for ticker '{stock_symbol.upper()}'. Please verify the NSE symbol.")
            else:
                # Use Streamlit columns to present the live financial indicators neatly
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric(
                        label="Current Price", 
                        value=f"₹{company.get('current_price', 'N/A')}"
                    )
                with col2:
                    st.metric(
                        label="52-Week(year) High", 
                        value=f"₹{company.get('fifty_two_week_high', 'N/A')}"
                    )
                with col3:
                    st.metric(
                        label="52-Week(year) Low", 
                        value=f"₹{company.get('fifty_two_week_low', 'N/A')}"
                    )
                
                # Sub-row of metrics for Market Cap and Dividends
                col4, col5 = st.columns(2)
                with col4:
                    mkt_cap = company.get('market_cap', 'N/A')
                    if isinstance(mkt_cap, (int, float)):
                        st.metric(label="Market Cap", value=f"₹{mkt_cap:,.0f}")
                    else:
                        st.metric(label="Market Cap", value=mkt_cap)
                with col5:
                    div_yield = company.get('dividend_yield', 'N/A')
                    if isinstance(div_yield, (int, float)):
                        st.metric(label="Dividend Yield", value=f"{div_yield * 100:.2f}%")
                    else:
                        st.metric(label="Dividend Yield", value=div_yield)
                
                # Professional Profile Information Markdown Section
                st.markdown("### Corporate Profile")
                st.write(f"**Company Name:** {company.get('name', stock_symbol.upper())}")            
                st.write(f"**Sector:** {company.get('sector', 'N/A')}")
                st.write(f"**Industry:** {company.get('industry', 'N/A')}")
                st.write(f"**Website:** [Visit Website]({company.get('website', '#')})")
                
                # --- AI INTEGRATION ---
                st.markdown("### GenAI Market Insights")
                
                with st.spinner("Consulting Gemini AI for industry insights..."):
                    ai_insight = get_ai_market_insight(
                        company_name=company.get('name', stock_symbol.upper()),
                        sector=company.get('sector', 'N/A'),
                        industry=company.get('industry', 'N/A')
                    )
                    st.info(ai_insight)


                    st.markdown("### 📰 Latest News")

                    articles = get_company_news(company.get('name', stock_symbol.upper()))

                    if articles:
                        for article in articles:
                            sentiment = analyze_sentiment(article["title"])
                            
                            st.write(f"**Title:** {article['title']}")
                            st.write(f"**Sentiment:** {sentiment}")
                            st.write(f"**Source:** {article['source']['name']}")
                            st.write(f"**Published:** {article['publishedAt']}")
                            st.write(f"🔗 {article['url']}")
                            st.divider()
                    else:
                        st.warning("No news found for this company.")

                    
                #  PLOTLY CHART IMPLEMENTATION
                import plotly.graph_objects as go
                
                ticker_symbol = stock_symbol.upper() + ".NS"
                hist = get_historical_data(ticker_symbol, period="6mo")
                
                if not hist.empty:
                    fig = go.Figure()
                    fig.add_trace(
                        go.Scatter(
                            x=hist.index, 
                            y=hist["Close"], 
                            name="Close Price",
                            line=dict(color="#00FFCC", width=2)
                        )
                    )
                    
                    fig.update_layout(
                        title=f"{stock_symbol.upper()} 6-Month Historical Price Trend",
                        xaxis_title="Date",
                        yaxis_title="Price (INR)",
                        template="plotly_dark",
                        margin=dict(l=20, r=20, t=40, b=20)
                    )
                    
                    st.plotly_chart(fig, width='stretch')
                else:
                    st.warning("No historical pricing data available for this symbol.")
                    
        except Exception as e:
            st.error(f"An unexpected error occurred. Error details: {e}")