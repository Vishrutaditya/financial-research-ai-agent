"""
services/stock_data.py

Thin wrapper around yfinance with validation, so callers never have to
guess whether a `None` came from "field doesn't exist" vs "ticker is invalid".
"""

import yfinance as yf


class StockDataError(Exception):
    """Raised when stock data cannot be retrieved for a given symbol."""


def get_stock_info(symbol: str) -> dict:
    """
    Returns the complete raw info dict yfinance provides for a symbol.
    Raises StockDataError if the symbol is invalid or the request fails.
    """
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
    except Exception as e:
        raise StockDataError(f"Failed to fetch data for '{symbol}': {e}") from e

    if not info or (info.get("currentPrice") is None and info.get("regularMarketPrice") is None):
        raise StockDataError(f"No data found for symbol '{symbol}'.")

    return info


def get_historical_data(symbol: str, period: str = "6mo"):
    """
    Fetches historical OHLCV data from Yahoo Finance for a given ticker.
    Raises StockDataError on failure (network issues, bad symbol, etc).
    """
    try:
        stock = yf.Ticker(symbol)
        hist = stock.history(period=period)
        return hist
    except Exception as e:
        raise StockDataError(f"Failed to fetch historical data for '{symbol}': {e}") from e


def get_company_info(symbol: str) -> dict:
    """
    Returns the key company details used across the app. Raises
    StockDataError if the symbol doesn't resolve to a real company,
    instead of silently returning a dict full of Nones.
    """
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
    except Exception as e:
        raise StockDataError(f"Failed to fetch company info for '{symbol}': {e}") from e

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

    if company_data["sector"] is None and company_data["industry"] is None:
        raise StockDataError(
            f"Could not find a valid company profile for '{symbol}'. "
            "Please verify the NSE symbol."
        )

    return company_data