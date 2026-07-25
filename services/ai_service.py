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


def extract_stock_symbol(user_input: str) -> str | None:
    """
    Attempts to identify an Indian NSE stock symbol from user prompt.
    Returns uppercase symbol (e.g. 'TATAMOTORS') or None if input is conversational.
    """
    if not user_input or not user_input.strip():
        return None

    cleaned = user_input.strip().upper()
    # If the user typed just a single word symbol like "TATAMOTORS" or "RELIANCE.NS"
    words = [w.strip(".,!?()[]{}") for w in cleaned.split()]
    
    # Common words to filter out
    stop_words = {"ANALYZE", "CHECK", "SHOW", "WHAT", "IS", "THE", "PRICE", "OF", "STOCK", "FOR", "BUY", "SELL", "HOLD", "NEWS", "ABOUT", "HI", "HELLO", "THANKS", "THANK", "YOU", "PLEASE", "TELL", "ME", "SEARCH", "RESEARCH"}
    
    candidates = [w for w in words if w and w not in stop_words and len(w) >= 2]
    
    if len(candidates) == 1:
        symbol = candidates[0].removesuffix(".NS")
        if symbol.isalpha():
            return symbol
    elif len(words) == 1:
        symbol = words[0].removesuffix(".NS")
        if symbol.isalpha():
            return symbol

    return None


def get_ai_followup_response(user_prompt: str, chat_history: list, last_stock_context: dict = None) -> str:
    """
    Generates a conversational AI response to a follow-up question.
    """
    if _client is None:
        return "AI Assistant is unavailable: GEMINI_API_KEY is not configured in your .env file."

    system_instruction = (
        "You are an expert AI Financial Research Assistant styled like Google Gemini AI. "
        "Provide helpful, concise, accurate, and beautifully structured responses using Markdown formatting. "
        "Use bullet points, bold key figures, and financial insights when appropriate."
    )

    context_str = ""
    if last_stock_context:
        company_name = safe_get(last_stock_context, 'company_name', 'N/A')
        sector = safe_get(last_stock_context, 'sector', 'N/A')
        price = safe_get(last_stock_context, 'current_price', 'N/A')
        rsi = safe_get(last_stock_context, 'rsi', 'N/A')
        signal = safe_get(last_stock_context, 'rsi_signal', 'N/A')
        context_str = (
            f"\nCurrent active stock analysis context:\n"
            f"- Company: {company_name}\n"
            f"- Sector: {sector}\n"
            f"- Current Price: {price}\n"
            f"- RSI (14): {rsi} ({signal})\n"
        )

    # Format small history snippet
    history_text = ""
    recent_history = chat_history[-6:] if len(chat_history) > 6 else chat_history
    for msg in recent_history:
        role = "User" if msg.get("role") == "user" else "Assistant"
        content = msg.get("content") or ""
        if isinstance(content, str):
            history_text += f"{role}: {content[:300]}\n"

    full_prompt = (
        f"{system_instruction}\n"
        f"{context_str}\n"
        f"Recent Conversation History:\n{history_text}\n"
        f"User Question: {user_prompt}\n\n"
        f"Answer directly, professionally, and concisely:"
    )

    try:
        response = _client.models.generate_content(
            model="gemini-2.5-flash",
            contents=full_prompt,
        )
        return response.text.strip()
    except Exception as e:
        return f"Could not generate a response at this time. (Error: {e})"