from __future__ import annotations

import json
from pathlib import Path
import sys

from sqlalchemy.orm import Session

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.db.models import MarketDecision, MarketEvent, MarketFeature
from market_intelligence import MarketIntelligenceEngine, load_market_intelligence_config
from market_intelligence.models import DecisionResult
from market_intelligence.storage import MarketIntelligenceStorage


class MarketIntelligenceService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.config = load_market_intelligence_config(PROJECT_ROOT / "backend")
        self.storage = MarketIntelligenceStorage(self.config.storage_dir)
        self.engine = MarketIntelligenceEngine(self.config, self.storage)

    def analyze(self, asset: str, timeframe: str) -> DecisionResult:
        decision = self.engine.analyze_market(asset, timeframe)
        self._persist_decision(decision)
        self._persist_feature(decision)
        self._persist_events()
        self.db.commit()
        return decision

    def latest(self, asset: str) -> DecisionResult | None:
        row = (
            self.db.query(MarketDecision)
            .filter(MarketDecision.asset == asset)
            .order_by(MarketDecision.created_at.desc())
            .first()
        )
        if row is None:
            return None
        return DecisionResult.from_dict(
            {
                "asset": row.asset,
                "timeframe": row.timeframe,
                "action": row.action,
                "confidence_score": row.confidence_score,
                "technical_score": row.technical_score,
                "macro_score": row.macro_score,
                "risk_score": row.risk_score,
                "valid_until": row.valid_until.isoformat(),
                "reasons": json.loads(row.reasons_json or "[]"),
                "blocks": json.loads(row.blocks_json or "[]"),
                "created_at": row.created_at.isoformat(),
                "regime": row.regime,
                "data_sources": json.loads(row.data_sources_json or "[]"),
            }
        )

    def status(self) -> dict:
        latest = self.db.query(MarketDecision).order_by(MarketDecision.created_at.desc()).first()
        return {
            "mode": self.config.market_mode,
            "storage_dir": str(self.config.storage_dir),
            "latest_asset": latest.asset if latest else None,
            "latest_action": latest.action if latest else None,
            "min_confidence_score": self.config.min_confidence_score,
            "sources": {
                "oanda": bool(self.config.oanda_api_token),
                "binance": True,
                "fred": bool(self.config.fred_api_key),
                "bls": bool(self.config.bls_api_key),
            },
        }

    def _persist_decision(self, decision: DecisionResult) -> None:
        row = MarketDecision(
            asset=decision.asset,
            timeframe=decision.timeframe,
            action=decision.action,
            confidence_score=decision.confidence_score,
            technical_score=decision.technical_score,
            macro_score=decision.macro_score,
            risk_score=decision.risk_score,
            valid_until=decision.valid_until,
            reasons_json=json.dumps(decision.reasons, ensure_ascii=True),
            blocks_json=json.dumps(decision.blocks, ensure_ascii=True),
            regime=decision.regime,
            data_sources_json=json.dumps(decision.data_sources, ensure_ascii=True),
            created_at=decision.created_at,
        )
        self.db.add(row)

    def _persist_feature(self, decision: DecisionResult) -> None:
        row = MarketFeature(
            asset=decision.asset,
            timeframe=decision.timeframe,
            volatility_score=max(0.0, min(100.0, decision.risk_score)),
            technical_score=decision.technical_score,
            macro_score=decision.macro_score,
            risk_score=decision.risk_score,
            regime=decision.regime,
            summary_json=json.dumps({"reasons": decision.reasons, "blocks": decision.blocks}, ensure_ascii=True),
            created_at=decision.created_at,
        )
        self.db.add(row)

    def _persist_events(self) -> None:
        events = self.storage.load_events()
        for event in events[:10]:
            exists = (
                self.db.query(MarketEvent)
                .filter(MarketEvent.title == event.title, MarketEvent.event_time == event.event_time)
                .first()
            )
            if exists is not None:
                continue
            self.db.add(
                MarketEvent(
                    event_time=event.event_time,
                    title=event.title,
                    impact=event.impact,
                    source=event.source,
                    region=event.region,
                    related_assets_json=json.dumps(event.related_assets, ensure_ascii=True),
                    created_at=event.event_time,
                )
            )
