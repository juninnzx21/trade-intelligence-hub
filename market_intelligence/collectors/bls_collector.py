from __future__ import annotations

import json
from urllib import request

from market_intelligence.config import MarketIntelligenceConfig
from market_intelligence.models import CollectorIssue


class BlsCollector:
    def __init__(self, config: MarketIntelligenceConfig) -> None:
        self.config = config

    def fetch_latest(self, series_ids: list[str]) -> tuple[dict[str, float], list[CollectorIssue]]:
        payload = {"seriesid": series_ids, "latest": True}
        if self.config.bls_api_key:
            payload["registrationkey"] = self.config.bls_api_key
        data = json.dumps(payload).encode("utf-8")
        req = request.Request(
            "https://api.bls.gov/publicAPI/v2/timeseries/data/",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=self.config.request_timeout_seconds) as response:
                result = json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            return {}, [CollectorIssue(source="bls", message=f"Falha ao consultar BLS: {exc}", critical=False)]

        values: dict[str, float] = {}
        for series in result.get("Results", {}).get("series", []):
            entries = series.get("data", [])
            if not entries:
                continue
            try:
                values[series["seriesID"]] = float(entries[0]["value"])
            except Exception:
                continue
        if not values:
            return {}, [CollectorIssue(source="bls", message="BLS sem valores utilizaveis.", critical=False)]
        return values, []
