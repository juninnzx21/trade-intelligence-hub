from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from market_intelligence.api_client import MarketIntelligenceApiClient


class MockResponse(BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_market_api_client_analyze_uses_mock(monkeypatch) -> None:
    payload = {
        "asset": "EUR/USD",
        "timeframe": "M1",
        "action": "NAO_OPERAR",
        "confidence_score": 42,
        "technical_score": 50,
        "macro_score": 25,
        "risk_score": 80,
        "valid_until": "2026-05-03T12:00:00+00:00",
        "reasons": ["dados insuficientes"],
        "blocks": ["Fonte critica indisponivel."],
        "created_at": "2026-05-03T11:59:00+00:00",
        "regime": "DESCONHECIDO",
        "data_sources": ["oanda"],
    }

    def fake_urlopen(req, timeout=0):
        return MockResponse(json.dumps(payload).encode("utf-8"))

    monkeypatch.setattr("market_intelligence.api_client.request.urlopen", fake_urlopen)
    client = MarketIntelligenceApiClient("https://example.com", token="secret")
    result = client.analyze("EUR/USD", "M1")
    assert result.asset == "EUR/USD"
    assert result.action == "NAO_OPERAR"
