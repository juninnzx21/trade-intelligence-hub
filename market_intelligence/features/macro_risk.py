from __future__ import annotations

from datetime import datetime, timedelta

from market_intelligence.config import MarketIntelligenceConfig
from market_intelligence.models import MacroEvent


def compute_macro_snapshot(
    config: MarketIntelligenceConfig,
    now: datetime,
    events: list[MacroEvent],
    dollar_strength_score: float,
) -> tuple[float, str, list[str]]:
    reasons: list[str] = []
    for event in events:
        delta_minutes = (event.event_time - now).total_seconds() / 60
        if -config.block_news_minutes_after <= delta_minutes <= config.block_news_minutes_before:
            reasons.append(f"Evento macro de alto impacto proximo: {event.title}.")
            return 20.0, "NOTICIA_PROXIMA", reasons

    if dollar_strength_score >= 70:
        reasons.append("Dolar relativamente forte no contexto atual.")
        return 64.0, "TENDENCIA", reasons
    if dollar_strength_score <= 35:
        reasons.append("Proxy do dolar enfraquecida no contexto atual.")
        return 58.0, "TENDENCIA", reasons
    return 55.0, "NORMAL", reasons
