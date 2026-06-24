print("Stock Data Service Loaded")
import yfinance as yf

ticker = yf.Ticker("TCS.NS")

info = ticker.info

print("Company:", info.get("longName"))
print("Current Price:", info.get("currentPrice"))