from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import CandleRecord, DecisionSignal, ForwardTestMetric, SignalResult


def evaluate_open_signals(db: Session) -> dict[str, int]:
    results = {"evaluated": 0, "wins": 0, "losses": 0, "discarded": 0}
    open_results = db.scalars(
        select(SignalResult).where(SignalResult.outcome_label == "PENDING")
    ).all()

    for result in open_results:
        signal = db.get(DecisionSignal, result.signal_id)
        if not signal or signal.decision == "NAO_OPERAR" or not signal.exit_time:
            result.outcome_label = "SKIPPED"
            result.status = "skipped"
            results["discarded"] += 1
            continue

        candle = db.scalars(
            select(CandleRecord)
            .where(
                CandleRecord.asset == signal.asset,
                CandleRecord.timeframe == signal.timeframe,
                CandleRecord.timestamp >= signal.exit_time - timedelta(minutes=max(signal.duration_minutes or 1, 1)),
            )
            .order_by(CandleRecord.timestamp.desc())
        ).first()
        if not candle:
            continue

        results["evaluated"] += 1
        if signal.decision == "COMPRA":
            won = candle.close > candle.open
        else:
            won = candle.close < candle.open

        result.status = "closed"
        result.outcome_label = "WIN" if won else "LOSS"
        result.pnl_units = 1.0 if won else -1.0
        result.notes = "Avaliacao automatica do forward test observer."
        if won:
            results["wins"] += 1
        else:
            results["losses"] += 1

    if results["evaluated"]:
        metric = db.scalars(select(ForwardTestMetric).where(ForwardTestMetric.window_name == "institutional-forward")).first()
        win_rate = round((results["wins"] / results["evaluated"]) * 100, 2)
        if metric:
            metric.signals_count += results["evaluated"]
            metric.win_rate = win_rate
            metric.status = "validando"
            metric.notes = "Atualizado automaticamente a partir dos sinais fechados."
        else:
            db.add(
                ForwardTestMetric(
                    window_name="institutional-forward",
                    signals_count=results["evaluated"],
                    win_rate=win_rate,
                    average_score=70.0,
                    status="validando",
                    notes="Atualizado automaticamente a partir dos sinais fechados.",
                )
            )
    db.commit()
    return results
