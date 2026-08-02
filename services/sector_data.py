"""
services/sector_data.py

Sector breakdown and peer benchmarking for Indian Stock Market (NSE / BSE).
"""

from typing import Any, Dict, List, Optional

INDIAN_SECTORS: Dict[str, Dict[str, Any]] = {
    "Technology": {
        "index_symbol": "^CNXIT",
        "index_name": "NIFTY IT Index",
        "peers": [
            {"symbol": "TCS.NS", "name": "Tata Consultancy Services"},
            {"symbol": "INFY.NS", "name": "Infosys Ltd"},
            {"symbol": "WIPRO.NS", "name": "Wipro Ltd"},
            {"symbol": "HCLTECH.NS", "name": "HCL Technologies"},
            {"symbol": "TECHM.NS", "name": "Tech Mahindra"},
            {"symbol": "540005.BO", "name": "LTIMindtree"},
        ],
    },
    "Financial Services": {
        "index_symbol": "^NSEBANK",
        "index_name": "NIFTY Bank Index",
        "peers": [
            {"symbol": "HDFCBANK.NS", "name": "HDFC Bank Ltd"},
            {"symbol": "ICICIBANK.NS", "name": "ICICI Bank Ltd"},
            {"symbol": "SBIN.NS", "name": "State Bank of India"},
            {"symbol": "AXISBANK.NS", "name": "Axis Bank Ltd"},
            {"symbol": "KOTAKBANK.NS", "name": "Kotak Mahindra Bank"},
            {"symbol": "BAJFINANCE.NS", "name": "Bajaj Finance"},
        ],
    },
    "Automobile": {
        "index_symbol": "^CNXAUTO",
        "index_name": "NIFTY Auto Index",
        "peers": [
            {"symbol": "TMPV.NS", "name": "Tata Motors Ltd"},
            {"symbol": "MARUTI.NS", "name": "Maruti Suzuki India"},
            {"symbol": "M&M.NS", "name": "Mahindra & Mahindra"},
            {"symbol": "BAJAJ-AUTO.NS", "name": "Bajaj Auto Ltd"},
            {"symbol": "HEROMOTOCO.NS", "name": "Hero MotoCorp"},
            {"symbol": "EICHERMOT.NS", "name": "Eicher Motors"},
        ],
    },
    "Energy": {
        "index_symbol": "^CNXENERGY",
        "index_name": "NIFTY Energy Index",
        "peers": [
            {"symbol": "RELIANCE.NS", "name": "Reliance Industries"},
            {"symbol": "ONGC.NS", "name": "ONGC Ltd"},
            {"symbol": "NTPC.NS", "name": "NTPC Ltd"},
            {"symbol": "POWERGRID.NS", "name": "Power Grid Corp"},
            {"symbol": "BPCL.NS", "name": "Bharat Petroleum"},
            {"symbol": "COALINDIA.NS", "name": "Coal India"},
        ],
    },
    "Consumer Goods": {
        "index_symbol": "^CNXFMCG",
        "index_name": "NIFTY FMCG Index",
        "peers": [
            {"symbol": "HINDUNILVR.NS", "name": "Hindustan Unilever"},
            {"symbol": "ITC.NS", "name": "ITC Ltd"},
            {"symbol": "NESTLEIND.NS", "name": "Nestle India"},
            {"symbol": "BRITANNIA.NS", "name": "Britannia Industries"},
            {"symbol": "DABUR.NS", "name": "Dabur India"},
            {"symbol": "VBL.NS", "name": "Varun Beverages"},
        ],
    },
    "Healthcare": {
        "index_symbol": "^CNXPHARMA",
        "index_name": "NIFTY Pharma Index",
        "peers": [
            {"symbol": "SUNPHARMA.NS", "name": "Sun Pharma"},
            {"symbol": "CIPLA.NS", "name": "Cipla Ltd"},
            {"symbol": "DRREDDY.NS", "name": "Dr Reddy's Labs"},
            {"symbol": "DIVISLAB.NS", "name": "Divi's Laboratories"},
            {"symbol": "APOLLOHOSP.NS", "name": "Apollo Hospitals"},
        ],
    },
    "Basic Materials": {
        "index_symbol": "^CNXMETAL",
        "index_name": "NIFTY Metal Index",
        "peers": [
            {"symbol": "TATASTEEL.NS", "name": "Tata Steel Ltd"},
            {"symbol": "JSWSTEEL.NS", "name": "JSW Steel"},
            {"symbol": "HINDALCO.NS", "name": "Hindalco Industries"},
            {"symbol": "VEDL.NS", "name": "Vedanta Ltd"},
        ],
    },
}


def map_to_indian_sector(sector_str: str) -> str:
    """Maps yfinance sector string to Indian sector keys."""
    if not sector_str or sector_str == "N/A":
        return "Technology"
    
    s_lower = sector_str.lower()
    if "tech" in s_lower or "software" in s_lower or "information" in s_lower:
        return "Technology"
    elif "financial" in s_lower or "bank" in s_lower or "insurance" in s_lower:
        return "Financial Services"
    elif "auto" in s_lower or "vehicle" in s_lower or "car" in s_lower:
        return "Automobile"
    elif "energy" in s_lower or "oil" in s_lower or "power" in s_lower or "gas" in s_lower:
        return "Energy"
    elif "consumer" in s_lower or "fmcg" in s_lower or "defensive" in s_lower:
        return "Consumer Goods"
    elif "health" in s_lower or "pharma" in s_lower or "medical" in s_lower:
        return "Healthcare"
    elif "material" in s_lower or "metal" in s_lower or "steel" in s_lower or "mining" in s_lower:
        return "Basic Materials"
    
    return "Technology"


def get_sector_info(sector_str: str) -> Dict[str, Any]:
    """Returns sector details, index symbol, and key Indian peer tickers."""
    sec_key = map_to_indian_sector(sector_str)
    return INDIAN_SECTORS.get(sec_key, INDIAN_SECTORS["Technology"])
