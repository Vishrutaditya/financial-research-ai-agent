"""
services/fundamentals.py

Performs fundamental analysis, debt ratio evaluation, valuation scoring,
and financial health metrics breakdown for Indian equities.
"""

from typing import Any, Dict


def evaluate_fundamental_health(info: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluates key fundamental metrics (P/E, Debt to Equity, ROE, Revenue Growth)
    and computes a Fundamental Health Score (0-100) with visual badges.
    """
    score = 50  # Baseline
    badges = []

    # 1. Debt to Equity Evaluation
    de_ratio = info.get("debt_to_equity")
    de_badge = ("N/A", "gray")
    if de_ratio is not None:
        if de_ratio <= 0.3:
            score += 15
            de_badge = ("🟢 Low Debt / Debt Free", "green")
            badges.append("🟢 Debt-Free Balance Sheet")
        elif de_ratio <= 0.8:
            score += 8
            de_badge = ("🟡 Moderate Debt", "orange")
        elif de_ratio <= 1.5:
            score -= 5
            de_badge = ("🟠 Elevated Debt", "orange")
        else:
            score -= 15
            de_badge = ("🔴 High Debt Risk", "red")
            badges.append("⚠️ High Debt Level")

    # 2. Valuation (P/E Ratio & PEG Ratio)
    pe_ratio = info.get("pe_ratio")
    peg_ratio = info.get("peg_ratio")
    pe_badge = ("N/A", "gray")
    if pe_ratio is not None:
        if pe_ratio < 15:
            score += 12
            pe_badge = ("🟢 Low Valuation / Value Stock", "green")
            badges.append("💎 Value Valuation")
        elif pe_ratio <= 30:
            score += 5
            pe_badge = ("🟡 Reasonable Valuation", "blue")
        else:
            score -= 8
            pe_badge = ("🔴 Premium / High Valuation", "red")

    if peg_ratio is not None and 0 < peg_ratio < 1.0:
        score += 8
        badges.append("⚡ Undervalued Growth (PEG < 1.0)")

    # 3. Profitability (Return on Equity - ROE)
    roe = info.get("roe")
    roe_badge = ("N/A", "gray")
    if roe is not None:
        roe_pct = roe * 100 if roe <= 1.0 else roe
        if roe_pct >= 20:
            score += 15
            roe_badge = ("🟢 Excellent ROE (>20%)", "green")
            badges.append("🏆 High ROE")
        elif roe_pct >= 12:
            score += 8
            roe_badge = ("🟡 Good ROE (12-20%)", "blue")
        else:
            score -= 10
            roe_badge = ("🔴 Low Return on Equity", "red")

    # 4. Growth Metrics (Revenue Growth)
    rev_growth = info.get("revenue_growth")
    growth_badge = ("N/A", "gray")
    if rev_growth is not None:
        rev_pct = rev_growth * 100 if rev_growth <= 1.0 else rev_growth
        if rev_pct >= 15:
            score += 10
            growth_badge = ("🟢 High Revenue Growth", "green")
            badges.append("🚀 Strong YoY Revenue Growth")
        elif rev_pct >= 5:
            score += 4
            growth_badge = ("🟡 Stable Growth", "blue")
        else:
            score -= 8
            growth_badge = ("🔴 Sluggish / Negative Growth", "red")

    # Clamp Score between 10 and 95
    final_score = max(10, min(95, score))

    if final_score >= 75:
        rating = "STRONG FUNDAMENTALS"
        rating_color = "🟢"
    elif final_score >= 50:
        rating = "MODERATE / BALANCED"
        rating_color = "🟡"
    else:
        rating = "CAUTION / WEAK METRICS"
        rating_color = "🔴"

    return {
        "score": final_score,
        "rating": rating,
        "rating_color": rating_color,
        "badges": badges,
        "de_badge": de_badge,
        "pe_badge": pe_badge,
        "roe_badge": roe_badge,
        "growth_badge": growth_badge,
    }
