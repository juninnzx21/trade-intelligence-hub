from __future__ import annotations

from datetime import timedelta

from app.core.time import BRAZIL_TZ, utc_now
from app.schemas.analysis import SnapshotInput
from app.services.engines.common import TimingPlan


TIMEFRAME_TO_MINUTES = {"1m": 1, "5m": 5, "15m": 15, "1h": 60}


def build_signal_timing(payload: SnapshotInput) -> TimingPlan:
    minutes = TIMEFRAME_TO_MINUTES.get(payload.timeframe, 5)
    candle_open = payload.timestamp.astimezone(BRAZIL_TZ).replace(second=0, microsecond=0)
    now = utc_now().astimezone(BRAZIL_TZ).replace(microsecond=0)
    elapsed_seconds = max(0, int((now - candle_open).total_seconds()))
    candle_seconds = minutes * 60

    if elapsed_seconds >= int(candle_seconds * 0.8):
        entry_time = candle_open + timedelta(minutes=minutes * 2)
    else:
        entry_time = candle_open + timedelta(minutes=minutes)

    if entry_time <= now:
        entry_time = entry_time + timedelta(minutes=minutes)

    exit_time = entry_time + timedelta(minutes=minutes)
    valid_until = entry_time + timedelta(seconds=min(max(45, minutes * 30), 300))
    duration_reason = (
        "Duracao alinhada ao timeframe e ao fechamento do proximo candle valido em horario de Brasilia."
        if minutes < 60
        else "Duracao mais longa porque a leitura usa estrutura de 1 hora em horario de Brasilia."
    )
    duration_label = f"{minutes} minutos" if minutes < 60 else "1 hora"
    return TimingPlan(
        entry_time=entry_time,
        exit_time=exit_time,
        duration_minutes=minutes,
        duration_label=duration_label,
        duration_reason=duration_reason,
        signal_valid_until=valid_until,
    )
