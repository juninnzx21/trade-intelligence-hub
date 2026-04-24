from __future__ import annotations

import asyncio

from sqlalchemy import select

from app.core.config import get_settings
from app.core.logging import log_event
from app.db.base import SessionLocal
from app.db.models import MonitoredAsset
from app.services.analysis import AnalysisEngine
from app.services.backtest import sync_backtest_metrics
from app.services.dashboard import build_live_board
from app.services.forward_test import evaluate_open_signals


async def run_collector_loop() -> None:
    settings = get_settings()
    while True:
        db = SessionLocal()
        try:
            engine = AnalysisEngine(db)
            assets = db.scalars(select(MonitoredAsset).where(MonitoredAsset.enabled == 1).order_by(MonitoredAsset.priority.asc())).all()
            board = []
            for asset in assets:
                timeframe = [part.strip() for part in asset.timeframes.split(",") if part.strip()][0]
                board.append(engine.analyze_live_asset(asset.symbol, asset.market, timeframe, persist=True))
            build_live_board(db, persist=False)
            sync_backtest_metrics(db)
            evaluate_open_signals(db)
            log_event("info", "collector_tick", assets=len(assets))
        finally:
            db.close()
        await asyncio.sleep(settings.collector_poll_seconds)
