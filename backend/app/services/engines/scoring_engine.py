from __future__ import annotations


def calculate_final_score(technical_score: float, fundamental_score: float, historical_score: float) -> float:
    return round((technical_score * 0.45) + (fundamental_score * 0.25) + (historical_score * 0.30), 2)


def decision_from_score(score: float, trend: str) -> str:
    if score <= 50:
        return "NAO_OPERAR"
    if trend.lower() in {"alta", "bullish"}:
        return "COMPRA"
    if trend.lower() in {"baixa", "bearish"}:
        return "VENDA"
    return "NAO_OPERAR"


def risk_level_from_context(score: float, volatility: float, spread: float) -> str:
    if score >= 76 and volatility <= 2.4 and spread <= 1.2:
        return "Baixo"
    if score >= 60 and volatility <= 3.0 and spread <= 2.0:
        return "Moderado"
    return "Alto"
