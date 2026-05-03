from __future__ import annotations

import json
from urllib import parse, request

from market_intelligence.config import MarketIntelligenceConfig
from market_intelligence.models import CollectorIssue


class FredCollector:
    def __init__(self, config: MarketIntelligenceConfig) -> None:
        self.config = config

    def fetch_latest(self, series_id: str) -> tuple[float | None, list[CollectorIssue]]:
        params = {"series_id": series_id, "file_type": "json", "sort_order": "desc", "limit": 1}
        if self.config.fred_api_key:
            params["api_key"] = self.config.fred_api_key
        url = f"https://api.stlouisfed.org/fred/series/observations?{parse.urlencode(params)}"
        try:
            with request.urlopen(url, timeout=self.config.request_timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            return None, [CollectorIssue(source="fred", message=f"Falha ao consultar FRED: {exc}", critical=False)]

        observations = payload.get("observations", [])
        if not observations:
            return None, [CollectorIssue(source="fred", message="FRED sem observacoes para a serie.", critical=False)]
        try:
            value = float(observations[0]["value"])
            return value, []
        except Exception:
            return None, [CollectorIssue(source="fred", message="Valor invalido retornado pela FRED.", critical=False)]
