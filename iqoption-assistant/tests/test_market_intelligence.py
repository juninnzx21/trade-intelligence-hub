from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import market_intelligence.decision_engine as decision_engine_module
from market_intelligence.config import MarketIntelligenceConfig
from market_intelligence.decision_engine import MarketIntelligenceEngine
from market_intelligence.models import CollectorIssue, DecisionResult, MacroEvent, MarketCandle
from market_intelligence.storage import MarketIntelligenceStorage


def build_config(tmp_path: Path, **overrides: object) -> MarketIntelligenceConfig:
    base = dict(
        root_dir=tmp_path,
        storage_dir=tmp_path / "storage",
        market_mode="local",
        market_api_url="",
        market_api_token="",
        oanda_api_token="demo-token",
        oanda_account_id="demo-account",
        oanda_base_url="https://api-fxpractice.oanda.com",
        fred_api_key="",
        bls_api_key="",
        min_confidence_score=70,
        block_news_minutes_before=30,
        block_news_minutes_after=15,
        request_timeout_seconds=5,
        fred_dxy_series_id="DTWEXBGS",
        fred_yield_series_id="DGS10",
        bls_cpi_series_id="CUUR0000SA0",
        bls_payroll_series_id="CES0000000001",
    )
    base.update(overrides)
    return MarketIntelligenceConfig(**base)


def rising_candles(source: str = "oanda", spread: float = 0.00004, count: int = 40) -> list[MarketCandle]:
    now = datetime.now(timezone.utc) - timedelta(minutes=count)
    rows: list[MarketCandle] = []
    price = 1.1000
    for index in range(count):
        open_price = price
        close_price = price + 0.00015
        rows.append(
            MarketCandle(
                timestamp=now + timedelta(minutes=index),
                open=open_price,
                high=close_price + 0.00005,
                low=open_price - 0.00003,
                close=close_price,
                volume=1000 + index,
                spread=spread,
                source=source,
            )
        )
        price = close_price
    return rows


def build_engine(tmp_path: Path, **config_overrides: object) -> MarketIntelligenceEngine:
    config = build_config(tmp_path, **config_overrides)
    storage = MarketIntelligenceStorage(config.storage_dir)
    return MarketIntelligenceEngine(config, storage)


def test_decision_with_data_insufficient_returns_no_operar(tmp_path: Path) -> None:
    engine = build_engine(tmp_path)
    engine.oanda.fetch_candles = lambda asset, timeframe: (rising_candles(count=5), [])  # type: ignore[method-assign]
    engine.fred.fetch_latest = lambda series_id: (100.0, [])  # type: ignore[method-assign]
    engine.bls.fetch_latest = lambda series_ids: ({}, [])  # type: ignore[method-assign]
    engine.calendar.fetch_upcoming_events = lambda now: ([], [])  # type: ignore[method-assign]
    result = engine.analyze_market("EUR/USD", "M1")
    assert result.action == "NAO_OPERAR"
    assert any("Dados insuficientes" in block for block in result.blocks)


def test_news_proxima_returns_no_operar(tmp_path: Path) -> None:
    engine = build_engine(tmp_path)
    engine.oanda.fetch_candles = lambda asset, timeframe: (rising_candles(), [])  # type: ignore[method-assign]
    engine.fred.fetch_latest = lambda series_id: (100.0, [])  # type: ignore[method-assign]
    engine.bls.fetch_latest = lambda series_ids: ({}, [])  # type: ignore[method-assign]
    engine.calendar.fetch_upcoming_events = lambda now: ([MacroEvent(event_time=now + timedelta(minutes=5), title="FOMC", impact="HIGH", source="fed", region="US")], [])  # type: ignore[method-assign]
    result = engine.analyze_market("EUR/USD", "M1")
    assert result.action == "NAO_OPERAR"
    assert any("Noticia macro" in block or "alto impacto" in reason for block in result.blocks for reason in [block])


def test_low_score_returns_no_operar(tmp_path: Path) -> None:
    engine = build_engine(tmp_path, min_confidence_score=95)
    engine.oanda.fetch_candles = lambda asset, timeframe: (rising_candles(spread=0.0006), [])  # type: ignore[method-assign]
    engine.fred.fetch_latest = lambda series_id: (100.0, [])  # type: ignore[method-assign]
    engine.bls.fetch_latest = lambda series_ids: ({}, [])  # type: ignore[method-assign]
    engine.calendar.fetch_upcoming_events = lambda now: ([], [])  # type: ignore[method-assign]
    result = engine.analyze_market("EUR/USD", "M1")
    assert result.action == "NAO_OPERAR"
    assert any("Score final abaixo" in block for block in result.blocks)


def test_strong_trend_without_blocks_returns_trade(tmp_path: Path, monkeypatch) -> None:
    engine = build_engine(tmp_path, min_confidence_score=55)
    monkeypatch.setattr(decision_engine_module, "compute_session_quality", lambda now: 82.0)
    engine.oanda.fetch_candles = lambda asset, timeframe: (rising_candles(), [])  # type: ignore[method-assign]
    engine.fred.fetch_latest = lambda series_id: (120.0, [])  # type: ignore[method-assign]
    engine.bls.fetch_latest = lambda series_ids: ({"CES0000000001": 200000.0}, [])  # type: ignore[method-assign]
    engine.calendar.fetch_upcoming_events = lambda now: ([], [])  # type: ignore[method-assign]
    result = engine.analyze_market("EUR/USD", "M1")
    assert result.action in {"COMPRA", "VENDA"}
    assert result.action == "COMPRA"
    assert result.confidence_score >= 55


def test_external_api_failure_returns_no_operar(tmp_path: Path) -> None:
    engine = build_engine(tmp_path, oanda_api_token="")
    result = engine.analyze_market("EUR/USD", "M1")
    assert result.action == "NAO_OPERAR"
    assert any("Fonte critica" in block or "OANDA" in block.upper() for block in result.blocks)


def test_decision_result_serialization_roundtrip(tmp_path: Path) -> None:
    now = datetime.now(timezone.utc)
    decision = DecisionResult(
        asset="EUR/USD",
        timeframe="M1",
        action="NAO_OPERAR",
        confidence_score=42.0,
        technical_score=50.0,
        macro_score=30.0,
        risk_score=80.0,
        valid_until=now + timedelta(minutes=2),
        reasons=["Teste"],
        blocks=["Bloqueio"],
        created_at=now,
        regime="LATERAL",
        data_sources=["oanda", "fred"],
    )
    restored = DecisionResult.from_dict(decision.to_dict())
    assert restored.asset == decision.asset
    assert restored.blocks == decision.blocks
    assert restored.data_sources == decision.data_sources
