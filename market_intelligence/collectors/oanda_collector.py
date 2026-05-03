from __future__ import annotations

import json
from datetime import datetime
from urllib import parse, request

from market_intelligence.config import MarketIntelligenceConfig
from market_intelligence.models import CollectorIssue, MarketCandle


class OandaCollector:
    def __init__(self, config: MarketIntelligenceConfig) -> None:
        self.config = config

    def fetch_candles(self, asset: str, timeframe: str, count: int = 120) -> tuple[list[MarketCandle], list[CollectorIssue]]:
        if not self.config.oanda_api_token:
            return [], [CollectorIssue(source="oanda", message="Token da OANDA ausente.", critical=True)]

        instrument = asset.replace("/", "_").upper()
        granularity = _oanda_granularity(timeframe)
        query = parse.urlencode({"price": "MBA", "granularity": granularity, "count": count})
        url = f"{self.config.oanda_base_url}/v3/instruments/{instrument}/candles?{query}"
        req = request.Request(url, headers={"Authorization": f"Bearer {self.config.oanda_api_token}", "Accept-Datetime-Format": "RFC3339"})
        try:
            with request.urlopen(req, timeout=self.config.request_timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            return [], [CollectorIssue(source="oanda", message=f"Falha ao consultar OANDA: {exc}", critical=True)]

        candles = []
        for item in payload.get("candles", []):
            mid = item.get("mid", {})
            bid = item.get("bid", {})
            ask = item.get("ask", {})
            try:
                bid_close = float(bid.get("c", mid.get("c", 0.0)))
                ask_close = float(ask.get("c", mid.get("c", 0.0)))
                candles.append(
                    MarketCandle(
                        timestamp=datetime.fromisoformat(item["time"].replace("Z", "+00:00")),
                        open=float(mid.get("o", 0.0)),
                        high=float(mid.get("h", 0.0)),
                        low=float(mid.get("l", 0.0)),
                        close=float(mid.get("c", 0.0)),
                        volume=float(item.get("volume", 0.0)),
                        spread=max(0.0, ask_close - bid_close),
                        source="oanda",
                    )
                )
            except Exception:
                continue
        if len(candles) < 10:
            return candles, [CollectorIssue(source="oanda", message="Dados insuficientes retornados pela OANDA.", critical=True)]
        return candles, []


def _oanda_granularity(timeframe: str) -> str:
    mapping = {"M1": "M1", "M5": "M5", "M15": "M15", "H1": "H1", "1m": "M1", "5m": "M5", "15m": "M15", "1h": "H1"}
    return mapping.get(timeframe.upper(), "M1")
