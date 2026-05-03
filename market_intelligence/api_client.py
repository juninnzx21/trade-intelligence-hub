from __future__ import annotations

import json
from urllib import error, parse, request

from market_intelligence.models import DecisionResult


class MarketIntelligenceApiClient:
    def __init__(self, base_url: str, token: str = "", timeout_seconds: int = 10) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout_seconds = timeout_seconds

    def analyze(self, asset: str, timeframe: str) -> DecisionResult:
        payload = self._request_json(
            "/api/v1/market/analyze",
            method="POST",
            payload={"asset": asset, "timeframe": timeframe},
        )
        return DecisionResult.from_dict(payload)

    def status(self) -> dict:
        return self._request_json("/api/v1/market/status")

    def latest(self, asset: str) -> dict:
        encoded_asset = parse.quote(asset, safe="")
        return self._request_json(f"/api/v1/market/latest?asset={encoded_asset}")

    def _request_json(self, path: str, method: str = "GET", payload: dict | None = None) -> dict:
        body = None
        headers = {"Accept": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = request.Request(f"{self.base_url}{path}", data=body, headers=headers, method=method)
        try:
            with request.urlopen(req, timeout=self.timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            raise RuntimeError(f"Falha na API de market intelligence: HTTP {exc.code}") from exc
        except error.URLError as exc:
            raise RuntimeError(f"Falha na API de market intelligence: {exc.reason}") from exc
