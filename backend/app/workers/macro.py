from __future__ import annotations

import asyncio
from datetime import timedelta

from sqlalchemy import select

from app.core.config import get_settings
from app.core.logging import log_event
from app.core.time import utc_now
from app.db.base import SessionLocal
from app.db.models import EconomicEvent, MarketNews


PUBLIC_HEADLINES = [
    ("Mercado monitora juros dos EUA e fluxo para dolar", "GLOBAL", "MEDIO"),
    ("Bitcoin oscila com sensibilidade a liquidez global", "BTC/USDT", "MEDIO"),
    ("Euro reage a leitura de inflacao e guidance do BCE", "EUR/USD", "MEDIO"),
]


async def run_macro_loop() -> None:
    settings = get_settings()
    cursor = 0
    while True:
        db = SessionLocal()
        try:
            title, scope, impact = PUBLIC_HEADLINES[cursor % len(PUBLIC_HEADLINES)]
            cursor += 1
            db.add(
                MarketNews(
                    published_at=utc_now(),
                    title=title,
                    impact=impact,
                    asset_scope=scope,
                    source="Public Macro Feed",
                    summary="Atualizacao publica sintetizada para enriquecer o contexto do motor.",
                )
            )
            existing = db.scalars(
                select(EconomicEvent).where(EconomicEvent.title == "Macro Monitor Window")
            ).first()
            if not existing:
                db.add(
                    EconomicEvent(
                        event_time=utc_now() + timedelta(minutes=45),
                        region="US",
                        title="Macro Monitor Window",
                        impact="MEDIO",
                        source="Public Macro Feed",
                        summary="Janela sintetica para exercitar filtros de calendario economico em modo observador.",
                    )
                )
            db.commit()
            log_event("info", "macro_tick", headline=title)
        finally:
            db.close()
        await asyncio.sleep(settings.macro_poll_seconds)
