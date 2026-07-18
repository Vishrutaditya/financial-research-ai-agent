"""
utils/helpers.py

Small, framework-agnostic helper functions shared across services and app.py.
Kept free of Streamlit/yfinance imports so they stay easy to unit test.
"""

from typing import Any, Iterable


def safe_get(data: dict, key: str, default: Any = "N/A") -> Any:
    """Get a value from a dict, returning `default` if missing or None."""
    if not data:
        return default
    value = data.get(key)
    return default if value is None else value


def format_currency(value, symbol: str = "₹") -> str:
    """Format a number as currency (e.g. ₹1,234,567). Passes non-numbers through."""
    if isinstance(value, (int, float)):
        return f"{symbol}{value:,.0f}"
    return value if value is not None else "N/A"


def format_percentage(value, decimals: int = 2) -> str:
    """Format a fraction (e.g. 0.025) as a percentage string ('2.50%')."""
    if isinstance(value, (int, float)):
        return f"{value * 100:.{decimals}f}%"
    return value if value is not None else "N/A"


def summarize_news_with_sentiment(articles_with_sentiment: Iterable[dict]) -> str:
    """
    Turns a list of {"title", "source", "sentiment"} dicts into a compact
    bullet-point block suitable for dropping straight into an LLM prompt.
    """
    lines = []
    for item in articles_with_sentiment or []:
        title = item.get("title", "Untitled")
        source = item.get("source", "Unknown source")
        sentiment = item.get("sentiment", "Neutral")
        lines.append(f"- {title} ({sentiment}) -- {source}")
    return "\n".join(lines) if lines else "No recent news available."