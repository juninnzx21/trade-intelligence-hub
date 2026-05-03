from __future__ import annotations

from math import sqrt

from market_intelligence.models import MarketCandle


def compute_volatility_score(candles: list[MarketCandle]) -> float:
    if len(candles) < 10:
        return 100.0
    returns = []
    for previous, current in zip(candles, candles[1:]):
        if previous.close:
            returns.append((current.close - previous.close) / previous.close)
    if not returns:
        return 100.0
    mean = sum(returns) / len(returns)
    variance = sum((value - mean) ** 2 for value in returns) / len(returns)
    std = sqrt(variance)
    return max(0.0, min(100.0, std * 4000))
