from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.schemas.analysis import SnapshotInput
from app.db.models import MarketSnapshot
from app.services.engines.common import ScoreBreakdown


def calculate_historical_score(db: Session, payload: SnapshotInput, snapshot: dict[str, float | str | bool]) -> ScoreBreakdown:
    score = 52.0
    reasons: list[str] = []
    similar = db.scalars(
        select(MarketSnapshot).where(
            MarketSnapshot.symbol == payload.symbol,
            MarketSnapshot.timeframe == payload.timeframe,
            MarketSnapshot.trend == payload.trend,
        )
    ).all()

    if not similar:
        return ScoreBreakdown(score=score, reasons=["Base historica inicial ainda curta para esse contexto."])

    successful = [item for item in similar if item.future_result.upper() in {"WIN", "TARGET", "POSITIVE"}]
    success_rate = len(successful) / len(similar)
    score += success_rate * 30
    reasons.append(f"Historico semelhante indica taxa positiva de {round(success_rate * 100, 1)}%.")

    current_hour = payload.timestamp.hour
    same_hour = [item for item in similar if item.created_at.hour == current_hour]
    if same_hour:
        score += 6
        reasons.append("Horario atual possui amostra comparavel registrada.")

    score += 4 if float(snapshot["volatility_pct"]) <= 2.4 else -4
    return ScoreBreakdown(score=max(0.0, min(round(score, 2), 100.0)), reasons=reasons)
