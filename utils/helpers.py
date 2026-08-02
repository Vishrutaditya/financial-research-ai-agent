"""
utils/helpers.py

Helper functions for formatting INR currencies, Indian market hours status calculation,
and percentage formatting.
"""

from datetime import datetime
import pytz


def safe_get(dictionary: dict, key: str, default: str = "N/A"):
    """Safely fetch key value from dictionary or return default."""
    if not isinstance(dictionary, dict):
        return default
    val = dictionary.get(key)
    return val if val is not None else default


def format_inr_currency(value, is_market_cap: bool = False) -> str:
    """
    Format numbers into Indian Rupee (INR - ₹) representation.
    Handles Lakhs (₹1 Lakh = ₹100,000) and Crores (₹1 Cr = ₹10,000,000).
    """
    if value is None or not isinstance(value, (int, float)):
        return "N/A"

    if is_market_cap:
        # Market Cap representation in Crores
        crores = value / 10_000_000
        if crores >= 100_000:
            lakh_crores = crores / 100_000
            return f"₹{lakh_crores:,.2f} Lakh Cr"
        elif crores >= 1:
            return f"₹{crores:,.2f} Cr"
        else:
            lakhs = value / 100_000
            return f"₹{lakhs:,.2f} Lakh"

    # Regular stock price / financial value formatting in Indian system
    return format_indian_number(value)


def format_indian_number(value: float, decimals: int = 2) -> str:
    """Format a number with Indian comma separation (e.g. 1,50,000.00)."""
    if value is None or not isinstance(value, (int, float)):
        return "N/A"

    is_negative = value < 0
    value = abs(value)

    formatted_float = f"{value:.{decimals}f}"
    parts = formatted_float.split(".")
    integer_part = parts[0]
    decimal_part = parts[1] if len(parts) > 1 else ""

    if len(integer_part) <= 3:
        result = integer_part
    else:
        last_three = integer_part[-3:]
        other_digits = integer_part[:-3]
        groups = []
        while len(other_digits) > 2:
            groups.insert(0, other_digits[-2:])
            other_digits = other_digits[:-2]
        if other_digits:
            groups.insert(0, other_digits)
        groups.append(last_three)
        result = ",".join(groups)

    formatted = f"₹{result}.{decimal_part}" if decimals > 0 else f"₹{result}"
    return f"-{formatted}" if is_negative else formatted


def format_percentage(value, decimals: int = 2) -> str:
    """Format a decimal or percentage fraction (e.g. 0.154 -> 15.40%)."""
    if value is None or not isinstance(value, (int, float)):
        return "N/A"
    
    # If already in percentage terms (> 1.0 or < -1.0) or small float
    val_pct = value if abs(value) > 2.0 else value * 100
    prefix = "+" if val_pct > 0 else ""
    return f"{prefix}{val_pct:.{decimals}f}%" if val_pct != 0 else f"0.00%"


def get_indian_market_status() -> dict:
    """
    Calculate current market state for Indian Stock Exchanges (NSE / BSE).
    Timezone: Asia/Kolkata (IST - UTC+5:30).
    Trading Days: Monday to Friday (weekday 0 to 4).
    Hours:
      - Pre-Market: 09:00 AM - 09:15 AM IST
      - Live Market: 09:15 AM - 03:30 PM IST (15:30)
      - Post-Market / Closed: After 03:30 PM IST or before 09:00 AM IST
    """
    ist = pytz.timezone("Asia/Kolkata")
    now_ist = datetime.now(ist)
    
    weekday = now_ist.weekday()  # 0: Monday, 6: Sunday
    current_time_str = now_ist.strftime("%d %b %Y, %I:%M:%S %p IST")
    
    # Check if weekend
    if weekday in (5, 6):
        return {
            "status": "Market Closed (Weekend)",
            "state": "CLOSED",
            "badge_color": "🔴",
            "current_time": current_time_str,
            "next_event": "Opens Monday at 09:15 AM IST",
        }

    time_minutes = now_ist.hour * 60 + now_ist.minute

    # 9:00 AM = 540 mins, 9:15 AM = 555 mins, 3:30 PM (15:30) = 930 mins
    pre_market_start = 9 * 60  # 540
    market_start = 9 * 60 + 15  # 555
    market_end = 15 * 60 + 30  # 930

    if pre_market_start <= time_minutes < market_start:
        return {
            "status": "Pre-Market Session (NSE/BSE)",
            "state": "PRE_MARKET",
            "badge_color": "🟡",
            "current_time": current_time_str,
            "next_event": "Live trading starts at 09:15 AM IST",
        }
    elif market_start <= time_minutes < market_end:
        mins_remaining = market_end - time_minutes
        hours_rem = mins_remaining // 60
        mins_rem = mins_remaining % 60
        rem_str = f"{hours_rem}h {mins_rem}m" if hours_rem > 0 else f"{mins_rem}m"
        return {
            "status": "🟢 Live Trading Open (NSE/BSE)",
            "state": "OPEN",
            "badge_color": "🟢",
            "current_time": current_time_str,
            "next_event": f"Closes in {rem_str} (at 3:30 PM IST)",
        }
    else:
        return {
            "status": "Market Closed",
            "state": "CLOSED",
            "badge_color": "🔴",
            "current_time": current_time_str,
            "next_event": "Opens next trading day at 09:15 AM IST",
        }


def summarize_news_with_sentiment(articles: list) -> str:
    """Format news articles into compact bullets for LLM insight context."""
    if not articles:
        return "No recent company news available."
    lines = []
    for item in articles[:5]:
        title = item.get("title", "Untitled")
        source = item.get("source", "Market News")
        sentiment = item.get("sentiment", "Neutral")
        lines.append(f"- {title} ({sentiment}) [{source}]")
    return "\n".join(lines)
