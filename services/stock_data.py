import yfinance as yf


def get_stock_info(symbol):
    """
    Returns complete stock information.
    """
    ticker = yf.Ticker(symbol)
    return ticker.info


def get_historical_data(symbol, period="6mo"):
    """
    Fetches historical price data from Yahoo Finance for a given ticker symbol.
    """
    stock = yf.Ticker(symbol)
    hist = stock.history(period=period)
    return hist


def get_company_info(symbol):
    """
    Returns only the important company details.
    """
    ticker = yf.Ticker(symbol)
    info = ticker.info
    company_data = {
        "name": info.get("longName"),
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "website": info.get("website"),
        "market_cap": info.get("marketCap"),
        "current_price": info.get("currentPrice") or info.get("regularMarketPrice"),
        "fifty_two_week_high": info.get("fiftyTwoWeekHigh"),
        "fifty_two_week_low": info.get("fiftyTwoWeekLow"),
        "dividend_yield": info.get("dividendYield"),
}
    return company_data