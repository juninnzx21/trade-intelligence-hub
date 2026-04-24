from __future__ import annotations

from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import BacktestMetric, MarketSnapshot


def run_backtest_report(db: Session) -> list[dict]:
    snapshots = db.scalars(select(MarketSnapshot).order_by(MarketSnapshot.created_at.asc())).all()
    grouped: dict[tuple[str, str], list[MarketSnapshot]] = defaultdict(list)
    for item in snapshots:
        grouped[(item.symbol, item.timeframe)].append(item)

    report: list[dict] = []
    for (symbol, timeframe), items in grouped.items():
        closed = [item for item in items if item.future_result.upper() not in {"PENDING", "NEUTRAL"}]
        if not closed:
            continue
        wins = [item for item in closed if item.future_result.upper() in {"WIN", "TARGET", "POSITIVE"}]
        losses = [item for item in closed if item.future_result.upper() in {"LOSS", "NEGATIVE"}]
        win_rate = round((len(wins) / len(closed)) * 100, 2)
        avg_win = sum(item.final_score for item in wins) / len(wins) if wins else 0.0
        avg_loss = sum(item.final_score for item in losses) / len(losses) if losses else 1.0
        payoff = round(avg_win / avg_loss, 2) if avg_loss else 0.0
        pnl_curve = []
        running = 0.0
        for item in closed:
            running += 1.0 if item in wins else -1.0
            pnl_curve.append(running)
        peak = pnl_curve[0] if pnl_curve else 0.0
        drawdown = 0.0
        for value in pnl_curve:
            peak = max(peak, value)
            drawdown = min(drawdown, value - peak)
        report.append(
            {
                "symbol": symbol,
                "timeframe": timeframe,
                "signals": len(closed),
                "win_rate": win_rate,
                "payoff": payoff,
                "drawdown": round(abs(drawdown), 2),
                "best_hour": max(items, key=lambda row: row.final_score).created_at.strftime("%H:00 UTC"),
                "worst_hour": min(items, key=lambda row: row.final_score).created_at.strftime("%H:00 UTC"),
            }
        )
    return sorted(report, key=lambda item: item["win_rate"], reverse=True)


def sync_backtest_metrics(db: Session) -> list[dict]:
    report = run_backtest_report(db)
    for row in report:
        existing = db.scalars(
            select(BacktestMetric).where(BacktestMetric.symbol == row["symbol"], BacktestMetric.timeframe == row["timeframe"])
        ).first()
        if existing:
            existing.win_rate = row["win_rate"]
            existing.payoff = row["payoff"]
            existing.drawdown = row["drawdown"]
            existing.net_profit = round(row["signals"] * ((row["win_rate"] / 100) - (1 - row["win_rate"] / 100)), 2)
            existing.best_hour = row["best_hour"]
        else:
            db.add(
                BacktestMetric(
                    strategy_name="Institutional Replay",
                    symbol=row["symbol"],
                    timeframe=row["timeframe"],
                    win_rate=row["win_rate"],
                    payoff=row["payoff"],
                    drawdown=row["drawdown"],
                    net_profit=round(row["signals"] * ((row["win_rate"] / 100) - (1 - row["win_rate"] / 100)), 2),
                    worst_streak=0,
                    best_hour=row["best_hour"],
                    risk_label="Moderado",
                )
            )
    db.commit()
    return report
