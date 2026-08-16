"""
services/ai_service.py

Generates GenAI market insights and comparative stock analysis using Google Gemini models.
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from google import genai
from utils.config import GEMINI_API_KEY
from utils.helpers import safe_get


from dotenv import load_dotenv, dotenv_values

def _get_api_key_details() -> Tuple[Optional[str], Optional[str]]:
    """
    Returns (api_key, error_message).
    Checks .env for GEMINI_API_KEY.
    """
    root_env = Path(__file__).resolve().parent.parent / ".env"
    env_key = None
    if root_env.exists():
        try:
            env_vars = dotenv_values(root_env)
            env_key = env_vars.get("GEMINI_API_KEY")
        except Exception:
            pass

    if not env_key:
        try:
            load_dotenv(root_env, override=True)
        except Exception:
            pass
        env_key = os.getenv("GEMINI_API_KEY") or GEMINI_API_KEY

    api_key = str(env_key or "").strip()
    if not api_key or api_key == "your_gemini_api_key_here":
        return None, "GEMINI_API_KEY is not configured in your `.env` file."

    return api_key, None


def _get_client() -> Optional[genai.Client]:
    """Dynamically get or instantiate GenAI client with current GEMINI_API_KEY from .env or env vars."""
    api_key, err = _get_api_key_details()
    if not api_key:
        return None

    try:
        return genai.Client(api_key=api_key)
    except Exception:
        return None


PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "financial_prompt.txt"

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
    "Give a 2-3 sentence fundamental insight followed by a concise Buy/Sell/Hold call with justification."
)


def _load_prompt_template() -> str:
    try:
        text = PROMPT_PATH.read_text(encoding="utf-8")
        return text if text.strip() else _FALLBACK_TEMPLATE
    except FileNotFoundError:
        return _FALLBACK_TEMPLATE


def _call_gemini_with_fallback(client: genai.Client, contents: str) -> str:
    """
    Attempts generation with primary model ('gemini-flash-latest') and fallbacks.
    Formats rate-limit/quota and authentication error messages cleanly.
    """
    models_to_try = [
        "gemini-flash-latest",
        "gemini-flash-lite-latest",
        "gemini-2.0-flash",
        "gemini-2.0-flash-lite"
    ]
    last_error = None
    had_quota_error = False

    for model_name in models_to_try:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=contents,
            )
            if response and response.text:
                return response.text.strip()
        except Exception as e:
            last_error = e
            err_str = str(e)
            if any(k in err_str for k in ["API_KEY_INVALID", "API key not valid", "401", "UNAUTHENTICATED", "INVALID_ARGUMENT", "ACCESS_TOKEN_TYPE_UNSUPPORTED"]):
                return (
                    "⚠️ **Invalid or Unauthenticated Gemini API Key**:\n\n"
                    "The API key provided is invalid, unauthenticated, or expired.\n"
                    "• **Solution**: Get a fresh Gemini API key from [Google AI Studio](https://aistudio.google.com/app/apikey) "
                    "and update `GEMINI_API_KEY` in your `.env` file."
                )
            if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "Quota exceeded" in err_str:
                had_quota_error = True
                continue

    # If all models failed or hit quota
    if had_quota_error:
        return (
            "⚠️ **Gemini API Rate Limit / Free Quota Exceeded (429)**:\n\n"
            "All API keys created under the same Google Cloud Project share the same free-tier rate limits:\n"
            "• **Per-minute Limit (15 RPM)**: Wait **30 to 60 seconds** and try again.\n"
            "• **Daily Limit / Project Quota**: If you created multiple keys in the same project, they share one quota pool.\n"
            "• **Fix**: Enable Billing or set up Pay-As-You-Go in [Google AI Studio](https://aistudio.google.com/app/apikey) to lift free tier restrictions."
        )

    if last_error:
        return f"Could not generate AI insights at this time. ({last_error})"

    return "Could not generate AI content at this time."


def get_ai_market_insight(context: dict) -> str:
    """Generates strategic market insight for a single stock."""
    api_key, err_msg = _get_api_key_details()
    if err_msg or not api_key:
        return err_msg or "AI Insight unavailable: GEMINI_API_KEY is not configured or invalid in your .env file."

    client = _get_client()
    if client is None:
        return "AI Insight unavailable: Could not initialize Gemini client."

    template = _load_prompt_template()
    safe_context = {field: safe_get(context, field, "N/A") for field in _CONTEXT_FIELDS}

    try:
        prompt = template.format(**safe_context)
    except KeyError as e:
        return f"AI Insight unavailable: prompt template missing key {e}."

    return _call_gemini_with_fallback(client, prompt)


def get_ai_comparison_insight(stock_list: List[Dict[str, Any]]) -> str:
    """
    Generates a comparative analysis comparing 2 or more Indian stocks
    on valuation, debt health, growth metrics, and risk profile.
    """
    api_key, err_msg = _get_api_key_details()
    if err_msg or not api_key:
        return err_msg or "AI Comparison Summary unavailable: GEMINI_API_KEY is not configured or invalid in your .env file."

    client = _get_client()
    if client is None:
        return "AI Comparison Summary unavailable: Could not initialize Gemini client."

    if not stock_list or len(stock_list) < 2:
        return "Select at least 2 stocks to generate an AI comparative analysis."

    summary_bullets = []
    for s in stock_list:
        summary_bullets.append(
            f"- **{s.get('name')} ({s.get('symbol')})** [{s.get('exchange')}]: "
            f"Price: ₹{s.get('current_price')}, Market Cap: ₹{s.get('market_cap')}, "
            f"P/E: {s.get('pe_ratio')}, Debt/Equity: {s.get('debt_to_equity')}, "
            f"ROE: {s.get('roe')}, Rev Growth: {s.get('revenue_growth')}, "
            f"Health Score: {s.get('health', {}).get('score')}/100"
        )

    prompt = (
        "You are an expert Indian stock market equity analyst. "
        "Compare the following Indian stocks based on fundamentals, valuation, debt levels, and profitability:\n\n"
        + "\n".join(summary_bullets)
        + "\n\nProvide a structured 3-bullet point comparison breakdown:\n"
        "1. **Valuation & Pricing**: Compare relative P/E and valuation attractiveness.\n"
        "2. **Financial Health & Debt Risk**: Compare Debt/Equity ratios and balance sheet safety.\n"
        "3. **Comparative Verdict**: State which stock offers the best risk-reward profile for long-term investors and why."
    )

    return _call_gemini_with_fallback(client, prompt)


def extract_stock_symbol(user_input: str) -> Optional[str]:
    """Extracts stock ticker symbol from user search query."""
    if not user_input or not user_input.strip():
        return None

    cleaned = user_input.strip().upper()
    words = [w.strip(".,!?()[]{}") for w in cleaned.split()]
    
    stop_words = {
        "ANALYZE", "CHECK", "SHOW", "WHAT", "IS", "THE", "PRICE", "OF", "STOCK",
        "FOR", "BUY", "SELL", "HOLD", "NEWS", "ABOUT", "HI", "HELLO", "THANKS",
        "PLEASE", "TELL", "ME", "SEARCH", "RESEARCH", "COMPARE"
    }
    
    candidates = [w for w in words if w and w not in stop_words and len(w) >= 2]
    
    if len(candidates) == 1:
        return candidates[0]
    elif len(words) == 1:
        return words[0]

    return None


def get_ai_followup_response(user_prompt: str, chat_history: list, last_stock_context: dict = None) -> str:
    """Generates conversational response for general market follow-ups."""
    api_key, err_msg = _get_api_key_details()
    if err_msg or not api_key:
        return err_msg or "AI Assistant is unavailable: GEMINI_API_KEY is not configured or invalid in your .env file."

    client = _get_client()
    if client is None:
        return "AI Assistant is unavailable: Could not initialize Gemini client."

    system_instruction = (
        "You are an expert AI Financial Assistant specializing in Indian Stock Markets (NSE / BSE). "
        "Provide clear, professional, well-formatted Markdown answers focusing on Indian stocks, INR metrics, and market trends."
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
        f"Answer directly and concisely:"
    )

    return _call_gemini_with_fallback(client, full_prompt)

