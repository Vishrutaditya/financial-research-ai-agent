"""
services/comparison.py

Stock Comparison Engine for Indian Equities.
Provides side-by-side metric comparison matrices, normalized performance series,
best-in-class indicator analysis, and visual comparison data.
"""

from typing import Any, Dict, List, Tuple
import pandas as pd
import yfinance as yf

from services.fundamental import evaluate_fundamental_health
from services.stock_data import StockDataError, get_company_info, get_historical_data
from utils.helpers import format_inr_currency, format_percentage


def compare_stocks_fundamentals(
    symbols: List[str], preferred_exchange: str = "NSE"
) -> Tuple[List[Dict[str, Any]], Dict[str, Dict[str, Any]], Dict[str, Any]]:
    """
    Fetches fundamental metrics for multiple Indian stocks and compares them side by side.
    
    Returns:
      - stock_data_list: List of company info dicts
      - metrics_table: Dict of metric rows for tabular display
      - best_performers: Dict indicating which stock won each key metric
    """
    stock_data_list = []
    
    for sym in symbols:
        try:
            info = get_company_info(sym, preferred_exchange)
            health = evaluate_fundamental_health(info)
            info["health"] = health
            stock_data_list.append(info)
        except StockDataError:
            continue

    if not stock_data_list:
        return [], {}, {}

    # Find winners / best in class for key metrics
    best_performers = {}

    # Lowest P/E (filter out None or <= 0)
    valid_pe = [
        (s["symbol"], s["pe_ratio"])
        for s in stock_data_list
        if s.get("pe_ratio") is not None and s["pe_ratio"] > 0
    ]
    if valid_pe:
        best_performers["pe_ratio"] = min(valid_pe, key=lambda x: x[1])[0]

    # Lowest Debt/Equity
    valid_de = [
        (s["symbol"], s["debt_to_equity"])
        for s in stock_data_list
        if s.get("debt_to_equity") is not None
    ]
    if valid_de:
        best_performers["debt_to_equity"] = min(valid_de, key=lambda x: x[1])[0]

    # Highest ROE
    valid_roe = [
        (s["symbol"], s["roe"])
        for s in stock_data_list
        if s.get("roe") is not None
    ]
    if valid_roe:
        best_performers["roe"] = max(valid_roe, key=lambda x: x[1])[0]

    # Highest Revenue Growth
    valid_growth = [
        (s["symbol"], s["revenue_growth"])
        for s in stock_data_list
        if s.get("revenue_growth") is not None
    ]
    if valid_growth:
        best_performers["revenue_growth"] = max(valid_growth, key=lambda x: x[1])[0]

    # Highest Dividend Yield
    valid_div = [
        (s["symbol"], s["dividend_yield"])
        for s in stock_data_list
        if s.get("dividend_yield") is not None
    ]
    if valid_div:
        best_performers["dividend_yield"] = max(valid_div, key=lambda x: x[1])[0]

    # Highest Health Score
    best_performers["health_score"] = max(
        stock_data_list, key=lambda x: x["health"]["score"]
    )["symbol"]

    return stock_data_list, best_performers


def get_normalized_comparison_history(
    symbols: List[str], period: str = "6mo", preferred_exchange: str = "NSE"
) -> pd.DataFrame:
    """
    Fetches historical price data for multiple stocks and computes % normalized performance
    series starting at 0% (Base 100) for comparative Plotly chart overlay.
    """
    combined_df = pd.DataFrame()

    for sym in symbols:
        try:
            hist = get_historical_data(sym, period=period, preferred_exchange=preferred_exchange)
            if hist is not None and not hist.empty and "Close" in hist.columns:
                close_prices = hist["Close"].dropna()
                if not close_prices.empty:
                    first_price = close_prices.iloc[0]
                    # Normalized percentage change from start of period
                    norm_series = ((close_prices / first_price) - 1.0) * 100.0
                    
                    clean_name = sym.split(".")[0].upper()
                    combined_df[clean_name] = norm_series
        except StockDataError:
            continue

    return combined_df
