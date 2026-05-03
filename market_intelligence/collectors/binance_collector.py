from __future__ import annotations

import json
from datetime import datetime, timezone
from urllib import parse, request

from market_intelligence.config import MarketIntelligenceConfig
from market_intelligence.models import CollectorIssue, MarketCandle


class BinanceCollector:
    def __init__(self, config: MarketIntelligenceConfig) -> None:
        self.config = config

    def fetch_candles(self, asset: str, timeframe: str, limit: int = 120) -> tuple[list[MarketCandle], list[CollectorIssue]]:
        symbol = asset.replace("/", "").replace("-", "").upper()
        interval = _binance_interval(timeframe)
        query = parse.urlencode({"symbol": symbol, "interval": interval, "limit": limit})
        url = f"https://api.binance.com/api/v3/klines?{query}"
        try:
            with request.urlopen(url, timeout=self.config.request_timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            return [], [CollectorIssue(source="binance", message=f"Falha ao consultar Binance: {exc}", critical=True)]

        candles = [
            MarketCandle(
                timestamp=datetime.fromtimestamp(item[0] / 1000, tz=timezone.utc),
                open=float(item[1]),
                high=float(item[2]),
                low=float(item[3]),
                close=float(item[4]),
                volume=float(item[5]),
                spread=max(0.0, float(item[2]) - float(item[1])) * 0.0001,
                source="binance",
            )
            for item in payload
        ]
        return candles, []


def _binance_interval(timeframe: str) -> str:
    mapping = {"M1": "1m", "M5": "5m", "M15": "15m", "H1": "1h", "1m": "1m", "5m": "5m", "15m": "15m", "1h": "1h"}
    return mapping.get(timeframe.upper(), "1m")
