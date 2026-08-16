from datetime import datetime
import pytz


def get_market_status():
    """Calculates Indian stock market status (Mon-Fri 9:15 AM - 3:30 PM IST)."""
    ist = pytz.timezone("Asia/Kolkata")
    now_ist = datetime.now(ist)
    current_time_str = now_ist.strftime("%d %b %Y, %I:%M:%S %p IST")

    is_weekday = now_ist.weekday() < 5
    market_open = now_ist.replace(hour=9, minute=15, second=0)
    market_close = now_ist.replace(hour=15, minute=30, second=0)

    if is_weekday and market_open <= now_ist <= market_close:
        status = "🟢 Market Open"
        status_color = "#22c55e"
    else:
        status = "🔴 Market Closed"
        status_color = "#ef4444"

    return status, status_color, current_time_str