from __future__ import annotations

from market_intelligence.models import MarketCandle


def compute_trend_snapshot(candles: list[MarketCandle]) -> tuple[str, float]:
    if len(candles) < 20:
        return "INDEFINIDA", 0.0
    closes = [item.close for item in candles]
    short_ma = sum(closes[-7:]) / 7
    medium_ma = sum(closes[-20:]) / 20
    delta = short_ma - medium_ma
    if medium_ma == 0:
        return "INDEFINIDA", 0.0
    strength = max(0.0, min(100.0, abs(delta / medium_ma) * 8000))
    if delta > 0:
        return "ALTA", strength
    if delta < 0:
        return "BAIXA", strength
    return "LATERAL", 0.0
