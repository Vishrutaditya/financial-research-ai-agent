import streamlit as st
from services.stock_data import get_stock_info, get_historical_data, get_company_info
from services.ai_service import get_ai_market_insight

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
                # Format Market Cap cleanly
                mkt_cap = company.get('market_cap', 'N/A')
                if isinstance(mkt_cap, (int, float)):
                    st.metric(label="Market Cap", value=f"₹{mkt_cap:,.0f}")
                else:
                    st.metric(label="Market Cap", value=mkt_cap)
            with col5:
                div_yield = company.get('dividend_yield', 'N/A')
                # Format to percentage style if a float is provided
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
                # Pass the fresh data fields directly to the AI engine
                ai_insight = get_ai_market_insight(
                    company_name=company.get('name', stock_symbol.upper()),
                    sector=company.get('sector', 'N/A'),
                    industry=company.get('industry', 'N/A')
                )
                # Display the response inside a professional informational callout box
                st.info(ai_insight)
                
            #  PLOTLY CHART IMPLEMENTATION ---
            import plotly.graph_objects as go
            
            # Formulate the correct NSE ticker format
            ticker_symbol = stock_symbol.upper() + ".NS"
            
            # Fetch the 6-month historical dataframe
            hist = get_historical_data(ticker_symbol, period="6mo")
            
            if not hist.empty:
                # Build the interactive line graph
                fig = go.Figure()
                fig.add_trace(
                    go.Scatter(
                        x=hist.index, 
                        y=hist["Close"], 
                        name="Close Price",
                        line=dict(color="#00FFCC", width=2) # High-contrast trend line
                    )
                )
                
                # Apply professional dark mode layouts
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
            st.error(f"Could not retrieve details for token symbol '{stock_symbol.upper()}'. Please check the spelling or format. Error: {e}")