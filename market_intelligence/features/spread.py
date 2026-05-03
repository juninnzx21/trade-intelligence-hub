from __future__ import annotations

from market_intelligence.models import MarketCandle


def compute_spread_score(candles: list[MarketCandle]) -> float:
    spreads = [item.spread for item in candles[-20:] if item.spread >= 0]
    if not spreads:
        return 50.0
    average = sum(spreads) / len(spreads)
    return max(0.0, min(100.0, average * 10000))
