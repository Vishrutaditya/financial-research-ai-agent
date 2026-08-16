import streamlit as st
import plotly.express as px
import yfinance as yf
import pandas as pd

# Page Configuration
st.set_page_config(page_title="Financial Research AI", layout="wide")

# Title
st.title("📈 Financial Research AI")

# Sidebar
st.sidebar.title("📋 Menu")
st.sidebar.write("Stock Analysis Dashboard")

# Stock Input
stock = st.text_input("Enter Stock Symbol", "RELIANCE.NS")

# Analyze Button
if st.button("Analyze"):

    with st.spinner("Fetching stock data..."):

        try:
            # Download data
            data = yf.download(
                stock,
                period="1mo",
                interval="1d",
                auto_adjust=False,
                progress=False
            )

            if data.empty:
                st.error("❌ No data found. Please enter a valid stock symbol.")
            else:

                # Fix MultiIndex columns
                if isinstance(data.columns, pd.MultiIndex):
                    data.columns = data.columns.get_level_values(0)

                st.success(f"Showing analysis for {stock}")

                # Metrics
                current_price = float(data["Close"].iloc[-1])
                previous_price = float(data["Close"].iloc[-2])
                change = current_price - previous_price
                percent = (change / previous_price) * 100

                col1, col2 = st.columns(2)

                with col1:
                    st.metric(
                        "Current Price",
                        f"₹{current_price:.2f}"
                    )

                with col2:
                    st.metric(
                        "Today's Change",
                        f"{change:.2f}",
                        f"{percent:.2f}%"
                    )

                # Chart
                st.subheader("📊 Closing Price Chart")

                fig = px.line(
                    x=data.index,
                    y=data["Close"],
                    labels={
                        "x": "Date",
                        "y": "Closing Price"
                    },
                    title=f"{stock} Closing Price"
                )

                st.plotly_chart(fig, use_container_width=True)

                # Data Table
                st.subheader("📋 Last 5 Trading Days")

                st.dataframe(
                    data.tail().style.format("{:.2f}")
                )

        except Exception as e:
            st.error(f"Error: {e}")