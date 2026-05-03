from __future__ import annotations

from market_intelligence.models import FeatureSnapshot


def build_reasons(features: FeatureSnapshot, action_bias: str) -> list[str]:
    reasons = list(features.reasons)
    if features.trend_direction == "ALTA":
        reasons.append("Tendencia curta e media apontam alta.")
    elif features.trend_direction == "BAIXA":
        reasons.append("Tendencia curta e media apontam baixa.")
    else:
        reasons.append("Mercado sem direcao clara.")

    if features.volatility_score < 35:
        reasons.append("Volatilidade controlada para o timeframe.")
    elif features.volatility_score > 75:
        reasons.append("Volatilidade muito alta e exige cautela.")

    if features.macro_score >= 60:
        reasons.append("Contexto macro nao mostra bloqueio imediato.")
    else:
        reasons.append("Contexto macro reduz a confianca da entrada.")

    if action_bias == "COMPRA":
        reasons.append("Viés final favorece compra, sem certeza de execucao.")
    elif action_bias == "VENDA":
        reasons.append("Viés final favorece venda, sem certeza de execucao.")
    return reasons
