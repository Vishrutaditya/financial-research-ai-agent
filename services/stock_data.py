"""
services/stock_data.py

Fetches data from Yahoo Finance for Indian Stock Exchanges (NSE / BSE).
Handles .NS and .BO ticker suffixes, fundamental metrics (P/E, debt ratios, growth),
and historical OHLCV data with fallback handling for updated Yahoo Finance ticker symbols.
"""

from typing import Any, Dict, Optional, Tuple
import pandas as pd
import yfinance as yf


class StockDataError(Exception):
    """Raised when stock data cannot be retrieved for a given symbol."""


# Known ticker mappings for symbols where Yahoo Finance changed or updated its tickers
SYMBOL_ALIASES: Dict[str, str] = {
    "TATAMOTORS": "TMPV.NS",
    "TATAMOTORS.NS": "TMPV.NS",
    "TATAMOTORS.BO": "TMPV.BO",
    "LTIM": "540005.BO",
    "LTIM.NS": "540005.BO",
    "LTIM.BO": "540005.BO",
    "LTIMINDTREE": "540005.BO",
    "LTIMINDTREE.NS": "540005.BO",
    "LTIMINDTREE.BO": "540005.BO",
}

# User-friendly display symbol overrides
DISPLAY_SYMBOLS: Dict[str, str] = {
    "TMPV.NS": "TATAMOTORS",
    "TMPV.BO": "TATAMOTORS",
    "540005.BO": "LTIM",
}

DISPLAY_NAMES: Dict[str, str] = {
    "TMPV.NS": "Tata Motors Ltd",
    "TMPV.BO": "Tata Motors Ltd",
    "540005.BO": "LTIMindtree Ltd",
}


def normalize_symbol(symbol_input: str, preferred_exchange: str = "NSE") -> str:
    """
    Normalizes a user stock input string into a valid yfinance Indian ticker symbol.
    """
    sym = symbol_input.strip().upper()
    
    if sym in SYMBOL_ALIASES:
        return SYMBOL_ALIASES[sym]
    
    if sym.endswith(".NS") or sym.endswith(".BO"):
        return sym
    
    # If purely numeric, it's a BSE Scrip Code
    if sym.isdigit():
        return f"{sym}.BO"
    
    # If preferred_exchange is BSE
    if preferred_exchange.upper() in ("BSE", "BO"):
        return f"{sym}.BO"
    
    return f"{sym}.NS"


def get_company_info(symbol_input: str, preferred_exchange: str = "NSE") -> Dict[str, Any]:
    """
    Fetches comprehensive company fundamentals including valuation, debt ratios,
    growth metrics, and profile details.
    """
    ticker_symbol = normalize_symbol(symbol_input, preferred_exchange)
    ticker = yf.Ticker(ticker_symbol)
    
    info: Dict[str, Any] = {}
    try:
        info = ticker.info or {}
    except Exception:
        info = {}

    current_price = (
        info.get("currentPrice")
        or info.get("regularMarketPrice")
        or info.get("previousClose")
    )

    # Fallback to fast_info if info.get() returned None or info failed
    if current_price is None:
        try:
            fast_price = getattr(ticker.fast_info, "last_price", None)
            if fast_price is not None and not pd.isna(fast_price):
                current_price = float(fast_price)
        except Exception:
            pass

    # Fallback to recent history if fast_info and info both lacked price
    if current_price is None:
        try:
            hist = ticker.history(period="5d")
            if hist is not None and not hist.empty and "Close" in hist.columns:
                current_price = float(hist["Close"].iloc[-1])
        except Exception:
            pass

    # Retry with alternate exchange suffix if default exchange has no price data
    if current_price is None:
        alt_symbol = (
            ticker_symbol.replace(".NS", ".BO")
            if ticker_symbol.endswith(".NS")
            else ticker_symbol.replace(".BO", ".NS")
        )
        try:
            alt_ticker = yf.Ticker(alt_symbol)
            try:
                info = alt_ticker.info or {}
            except Exception:
                info = {}

            current_price = (
                info.get("currentPrice")
                or info.get("regularMarketPrice")
                or info.get("previousClose")
            )
            if current_price is None:
                fast_p = getattr(alt_ticker.fast_info, "last_price", None)
                if fast_p is not None and not pd.isna(fast_p):
                    current_price = float(fast_p)

            if current_price is None:
                hist = alt_ticker.history(period="5d")
                if hist is not None and not hist.empty and "Close" in hist.columns:
                    current_price = float(hist["Close"].iloc[-1])

            if current_price is not None:
                ticker_symbol = alt_symbol
                ticker = alt_ticker
        except Exception:
            pass

    if current_price is None and info.get("marketCap") is None:
        raise StockDataError(
            f"No valid trading data found for symbol '{symbol_input}'. "
            "Please check if the NSE (.NS) or BSE (.BO) symbol is correct."
        )

    # Determine Exchange name & Display Symbol
    exchange = "BSE" if ticker_symbol.endswith(".BO") else "NSE"
    raw_clean = ticker_symbol.split(".")[0]
    clean_symbol = DISPLAY_SYMBOLS.get(ticker_symbol, DISPLAY_SYMBOLS.get(symbol_input.strip().upper(), raw_clean))

    market_cap = info.get("marketCap")
    if market_cap is None:
        try:
            fast_mc = getattr(ticker.fast_info, "market_cap", None)
            if fast_mc is not None and not pd.isna(fast_mc):
                market_cap = float(fast_mc)
        except Exception:
            pass

    # Normalize Debt to Equity (yfinance usually returns D/E as percentage or ratio e.g. 45.2 -> 0.452)
    debt_to_equity_raw = info.get("debtToEquity")
    debt_to_equity = None
    if debt_to_equity_raw is not None:
        debt_to_equity = debt_to_equity_raw / 100.0 if debt_to_equity_raw > 10 else debt_to_equity_raw

    # Normalize Dividend Yield
    div_yield_raw = info.get("dividendYield")
    dividend_yield = None
    if div_yield_raw is not None:
        dividend_yield = div_yield_raw if div_yield_raw <= 1.0 else div_yield_raw / 100.0

    company_name = (
        info.get("longName")
        or info.get("shortName")
        or DISPLAY_NAMES.get(ticker_symbol)
        or clean_symbol
    )

    return {
        "symbol": clean_symbol,
        "ticker_symbol": ticker_symbol,
        "exchange": exchange,
        "name": company_name,
        "sector": info.get("sector", "N/A"),
        "industry": info.get("industry", "N/A"),
        "website": info.get("website", "#"),
        "summary": info.get("longBusinessSummary", ""),
        
        # Prices & Cap
        "current_price": current_price,
        "previous_close": info.get("regularMarketPreviousClose") or info.get("previousClose"),
        "open_price": info.get("regularMarketOpen") or info.get("open"),
        "day_high": info.get("dayHigh") or info.get("regularMarketDayHigh"),
        "day_low": info.get("dayLow") or info.get("regularMarketDayLow"),
        "fifty_two_week_high": info.get("fiftyTwoWeekHigh"),
        "fifty_two_week_low": info.get("fiftyTwoWeekLow"),
        "market_cap": market_cap,
        "volume": info.get("regularMarketVolume") or info.get("volume"),

        # Valuation Ratios
        "pe_ratio": info.get("trailingPE"),
        "forward_pe": info.get("forwardPE"),
        "pb_ratio": info.get("priceToBook"),
        "peg_ratio": info.get("pegRatio"),
        "ev_to_ebitda": info.get("enterpriseToEbitda"),
        "dividend_yield": dividend_yield,

        # Debt Ratios & Financial Health
        "total_debt": info.get("totalDebt"),
        "total_cash": info.get("totalCash"),
        "debt_to_equity": debt_to_equity,
        "current_ratio": info.get("currentRatio"),
        "quick_ratio": info.get("quickRatio"),

        # Profitability & Growth Metrics
        "roe": info.get("returnOnEquity"),
        "roa": info.get("returnOnAssets"),
        "revenue_growth": info.get("revenueGrowth"),
        "earnings_growth": info.get("earningsGrowth"),
        "operating_margin": info.get("operatingMargins"),
        "profit_margin": info.get("profitMargins"),
        "gross_margin": info.get("grossMargins"),
        
        # Per Share Metrics
        "trailing_eps": info.get("trailingEps"),
        "forward_eps": info.get("forwardEps"),
        "book_value": info.get("bookValue"),
    }


def get_historical_data(symbol_input: str, period: str = "6mo", preferred_exchange: str = "NSE") -> pd.DataFrame:
    """
    Fetches historical price data (OHLCV) for an Indian ticker.
    """
    ticker_symbol = normalize_symbol(symbol_input, preferred_exchange)
    
    try:
        stock = yf.Ticker(ticker_symbol)
        hist = stock.history(period=period)
        
        if hist is None or hist.empty:
            alt_symbol = (
                ticker_symbol.replace(".NS", ".BO")
                if ticker_symbol.endswith(".NS")
                else ticker_symbol.replace(".BO", ".NS")
            )
            stock = yf.Ticker(alt_symbol)
            hist = stock.history(period=period)
            
        if hist is None or hist.empty:
            raise StockDataError(f"No price history returned for '{symbol_input}'.")
            
        return hist
    except Exception as e:
        if isinstance(e, StockDataError):
            raise e
        raise StockDataError(f"Failed to fetch historical data for '{symbol_input}': {e}") from e
