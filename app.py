import streamlit as st
import yfinance as yf

st.title("Indian Stock Research Assistant")

stock_symbol = st.text_input(
    "Enter NSE Stock Symbol",
    "TCS"
)

if st.button("Analyze"):

    try:
        ticker = yf.Ticker(stock_symbol + ".NS")

        info = ticker.info

        st.success("Stock Data Retrieved")

        st.write("Company Name:", info.get("longName"))
        st.write("Current Price:", info.get("currentPrice"))
        st.write("Market Cap:", info.get("marketCap"))
        st.write("Sector:", info.get("sector"))

    except Exception as e:
        st.error(str(e))