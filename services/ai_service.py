"""
services/ai_service.py

Generates the GenAI market insight. Unlike the original version, this
consumes a single `context` dict assembled by app.py from every service
(company profile, technical indicators, news + sentiment) so the model
reasons over the full research picture instead of just sector/industry.
"""

from pathlib import Path

from google import genai

from utils.config import GEMINI_API_KEY
from utils.helpers import safe_get

# NOTE: this uses the `google-genai` package (from google import genai), not
# the old `google-generativeai` package (import google.generativeai as genai).
# The latter reached end-of-life -- no more bug/security fixes -- so if your
# requirements.txt still has google-generativeai, swap it for google-genai.
_client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "financial_prompt.txt"

# Keys the prompt template expects. Kept in one place so template and code
# can't silently drift apart.
_CONTEXT_FIELDS = [
    "company_name", "sector", "industry", "current_price", "market_cap",
    "fifty_two_week_high", "fifty_two_week_low", "dividend_yield",
    "sma", "ema", "rsi", "rsi_signal", "news_summary",
]

_FALLBACK_TEMPLATE = (
    "You are a financial analyst. Analyze {company_name} in the {sector} "
    "sector, {industry} industry. Current price {current_price}, market cap "
    "{market_cap}. Technicals: SMA {sma}, EMA {ema}, RSI {rsi} ({rsi_signal}). "
    "Recent news:\n{news_summary}\n\n"
    "Give a 2-3 sentence insight followed by a Buy/Sell/Hold call with justification."
)


def _load_prompt_template() -> str:
    try:
        text = PROMPT_PATH.read_text(encoding="utf-8")
        return text if text.strip() else _FALLBACK_TEMPLATE
    except FileNotFoundError:
        return _FALLBACK_TEMPLATE


def get_ai_market_insight(context: dict) -> str:
    """
    Generates a strategic market insight from the FULL research context.

    Args:
        context: dict assembled by app.py. Expected keys (any missing key
            is substituted with 'N/A' so a partial context never crashes):
            company_name, sector, industry, current_price, market_cap,
            fifty_two_week_high, fifty_two_week_low, dividend_yield,
            sma, ema, rsi, rsi_signal, news_summary

    Returns:
        The model's analysis as plain text, or a user-facing explanation
        if the key is missing or the request fails.
    """
    if _client is None:
        return "AI Insight unavailable: GEMINI_API_KEY is not configured in your .env file."

    template = _load_prompt_template()
    safe_context = {field: safe_get(context, field, "N/A") for field in _CONTEXT_FIELDS}

    try:
        prompt = template.format(**safe_context)
    except KeyError as e:
        return f"AI Insight unavailable: prompt template references unknown field {e}."

    try:
        response = _client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        return response.text.strip()
    except Exception as e:
        return f"Could not generate AI insights at this time. (Error: {e})"