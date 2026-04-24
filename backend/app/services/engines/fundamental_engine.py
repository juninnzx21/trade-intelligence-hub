from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.schemas.analysis import SnapshotInput
from app.db.models import EconomicEvent
from app.core.time import to_utc
from app.services.engines.common import ScoreBreakdown


def calculate_fundamental_score(db: Session, payload: SnapshotInput) -> ScoreBreakdown:
    score = 55.0
    reasons: list[str] = []
    now = to_utc(payload.timestamp)
    window_start = now - timedelta(hours=2)
    window_end = now + timedelta(hours=3)
    events = db.scalars(
        select(EconomicEvent).where(EconomicEvent.event_time >= window_start, EconomicEvent.event_time <= window_end)
    ).all()

    high_impact = [event for event in events if event.impact.upper() == "ALTO"]
    if high_impact:
        score -= 18
        reasons.append("Agenda economica carregada com evento de alto impacto.")
    else:
        score += 10
        reasons.append("Sem noticia forte proxima.")

    context = payload.context_news.lower()
    positive_terms = ("desinflacao", "liquidez", "corte de juros", "risk-on")
    negative_terms = ("guerra", "crise", "hawkish", "inflacao persistente", "fomc", "payroll")
    if any(term in context for term in positive_terms):
        score += 8
        reasons.append("Fluxo macro levemente favoravel ao ativo.")
    if any(term in context for term in negative_terms):
        score -= 10
        reasons.append("Sentimento macro pressiona a leitura atual.")

    return ScoreBreakdown(score=max(0.0, min(round(score, 2), 100.0)), reasons=reasons)
