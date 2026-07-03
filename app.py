import streamlit as st
from services.stock_data import get_stock_info, get_historical_data, get_company_info

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
            company = get_company_info(stock_symbol.upper() + ".NS")

            st.write("Company Name:", company["name"])
            st.write("Sector:", company["sector"])
            st.write("Industry:", company["industry"])
            st.write("Market Cap:", company["market_cap"])
            st.write("Website:", company["website"])

        except Exception as e:
            st.error(str(e))
    