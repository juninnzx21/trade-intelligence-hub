from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.time import to_utc, utc_now
from app.db.models import EconomicEvent, MarketSnapshot
from app.schemas.analysis import SnapshotInput
from app.services.engines.common import TimingPlan, ValidationResult


def validate_signal(
    db: Session,
    payload: SnapshotInput,
    snapshot: dict[str, float | str | bool],
    timing: TimingPlan,
) -> ValidationResult:
    blockers: list[str] = []
    warnings: list[str] = []

    if payload.spread > 2.5:
        blockers.append("Spread elevado para o contexto atual.")
    if payload.volatility > 4.2:
        blockers.append("Volatilidade anormal detectada.")

    candle_range = payload.high - payload.low
    body = abs(payload.close - payload.open)
    if candle_range and body / candle_range > 0.85:
        blockers.append("Candle excessivamente esticado.")

    if payload.trend.lower() == "lateral" and payload.volatility < 0.5:
        blockers.append("Mercado em lateralizacao extrema.")
    if bool(snapshot["lateral"]):
        blockers.append("Mercado sem direcao clara.")

    if timing.entry_time:
        seconds_to_entry = (timing.entry_time - payload.timestamp.astimezone(timing.entry_time.tzinfo)).total_seconds()
        if seconds_to_entry < 20:
            blockers.append("Faltam poucos segundos para o candle valido.")

    if timing.signal_valid_until and timing.entry_time and timing.signal_valid_until <= timing.entry_time:
        blockers.append("Validade inconsistente para o sinal.")

    event_window_start = to_utc(payload.timestamp)
    event_window_end = to_utc(timing.exit_time) if timing.exit_time else event_window_start + timedelta(minutes=30)
    critical_events = db.scalars(
        select(EconomicEvent).where(
            EconomicEvent.event_time >= event_window_start,
            EconomicEvent.event_time <= event_window_end,
            EconomicEvent.impact == "ALTO",
        )
    ).all()
    if critical_events:
        blockers.append("Noticia macro de alto impacto na janela operacional.")

    recent = db.scalars(
        select(MarketSnapshot).where(MarketSnapshot.symbol == payload.symbol).order_by(MarketSnapshot.created_at.desc())
    ).all()[:6]
    negative_streak = 0
    for item in recent:
        if item.future_result.upper() in {"LOSS", "NEGATIVE"}:
            negative_streak += 1
        else:
            break
    if negative_streak >= 3:
        blockers.append("Sequencia ruim recente para o ativo.")

    if float(snapshot["spread"]) > payload.spread * 1.8:
        blockers.append("Spread abriu demais no momento da leitura.")

    if abs(float(snapshot["momentum_pct"])) > 3:
        warnings.append("Movimento acelerado exige execucao disciplinada.")

    if timing.signal_valid_until and utc_now().astimezone(timing.signal_valid_until.tzinfo) > timing.signal_valid_until:
        blockers.append("Sinal expirado antes da exibicao.")

    return ValidationResult(blockers=blockers, warnings=warnings)
