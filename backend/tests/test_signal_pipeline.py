from pathlib import Path
import sys
from datetime import UTC, datetime

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.schemas.analysis import SnapshotInput
from app.services.engines.scoring_engine import decision_from_score
from app.services.engines.signal_timing_engine import build_signal_timing


def test_signal_timing_uses_brasilia_timezone():
    payload = SnapshotInput(
        symbol="EUR/USD",
        market="FOREX",
        timeframe="5m",
        open=1.08,
        high=1.081,
        low=1.079,
        close=1.0805,
        spread=0.4,
        volume=10000,
        volatility=1.2,
        trend="alta",
        context_news="sem noticia forte",
        timestamp=datetime(2026, 4, 24, 14, 30, tzinfo=UTC),
    )
    timing = build_signal_timing(payload)
    assert timing.entry_time is not None
    assert str(timing.entry_time.tzinfo) == "America/Sao_Paulo"


def test_score_decision_prefers_no_trade_below_threshold():
    assert decision_from_score(50, "alta") == "NAO_OPERAR"
    assert decision_from_score(70, "alta") == "COMPRA"
    assert decision_from_score(70, "baixa") == "VENDA"
