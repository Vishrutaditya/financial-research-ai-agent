import yfinance as yf


def get_stock_info(symbol):
    """
    Returns complete stock information.
    """
    ticker = yf.Ticker(symbol)
    return ticker.info


def get_historical_data(symbol, period="6mo"):
    """
    Returns historical stock prices.
    """
    ticker = yf.Ticker(symbol)
    return ticker.history(period=period)


def get_company_info(symbol):
    """
    Returns only the important company details.
    """
    ticker = yf.Ticker(symbol)
    info = ticker.info

    return {
        "name": info.get("longName"),
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "market_cap": info.get("marketCap"),
        "website": info.get("website")
    }