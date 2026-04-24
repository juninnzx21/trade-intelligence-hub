from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.db.models import EconomicEvent, MarketSnapshot
from app.schemas.analysis import AnalysisResponse, DashboardSummary, EconomicEventItem, OpportunityCard, SnapshotInput
from app.services.analysis import AnalysisEngine, summarize_reasons

router = APIRouter()


@router.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/dashboard/summary", response_model=DashboardSummary)
def dashboard_summary(db: Session = Depends(get_db)) -> DashboardSummary:
    total = db.scalar(select(func.count()).select_from(MarketSnapshot)) or 0
    buy = db.scalar(select(func.count()).select_from(MarketSnapshot).where(MarketSnapshot.decision == "COMPRA")) or 0
    sell = db.scalar(select(func.count()).select_from(MarketSnapshot).where(MarketSnapshot.decision == "VENDA")) or 0
    no_trade = db.scalar(select(func.count()).select_from(MarketSnapshot).where(MarketSnapshot.decision == "NAO_OPERAR")) or 0
    premium = db.scalar(select(func.count()).select_from(MarketSnapshot).where(MarketSnapshot.final_score >= 86)) or 0

    records = db.scalars(select(MarketSnapshot).order_by(MarketSnapshot.final_score.desc())).all()
    best_symbol = records[0].symbol if records else "-"
    best_timeframe = records[0].timeframe if records else "-"
    positive = [item for item in records if item.future_result.upper() in {"WIN", "TARGET", "POSITIVE"}]
    closed = [item for item in records if item.future_result.upper() not in {"PENDING", "NEUTRAL"}]
    win_rate = round((len(positive) / len(closed)) * 100, 2) if closed else 0.0
    active_alerts = db.scalar(
        select(func.count()).select_from(EconomicEvent).where(EconomicEvent.event_time >= datetime.now(timezone.utc))
    ) or 0

    return DashboardSummary(
        total_signals=total,
        buy_signals=buy,
        sell_signals=sell,
        no_trade_signals=no_trade,
        win_rate=win_rate,
        best_symbol=best_symbol,
        best_timeframe=best_timeframe,
        active_alerts=active_alerts,
        premium_opportunities=premium,
    )


@router.get("/signals")
def list_signals(db: Session = Depends(get_db)) -> list[dict]:
    records = db.scalars(select(MarketSnapshot).order_by(MarketSnapshot.created_at.desc())).all()
    return [
        {
            "id": item.id,
            "timestamp": item.created_at,
            "symbol": item.symbol,
            "market": item.market,
            "timeframe": item.timeframe,
            "decision": item.decision,
            "score": item.final_score,
            "risk_level": item.risk_level,
            "trend": item.trend,
            "reasoning": item.reasoning,
        }
        for item in records
    ]


@router.get("/opportunities", response_model=list[OpportunityCard])
def opportunities(db: Session = Depends(get_db)) -> list[OpportunityCard]:
    records = db.scalars(select(MarketSnapshot).order_by(MarketSnapshot.final_score.desc())).all()
    return [
        OpportunityCard(
            symbol=item.symbol,
            market=item.market,
            timeframe=item.timeframe,
            score=item.final_score,
            decision=item.decision,
            risk_level=item.risk_level,
            trend=item.trend,
            reasons=[part.strip() for part in item.reasoning.split("|") if part.strip()][:4],
        )
        for item in records[:6]
    ]


@router.get("/economic-events", response_model=list[EconomicEventItem])
def economic_events(db: Session = Depends(get_db)) -> list[EconomicEventItem]:
    records = db.scalars(select(EconomicEvent).order_by(EconomicEvent.event_time.asc())).all()
    return [
        EconomicEventItem(
            event_time=item.event_time,
            region=item.region,
            title=item.title,
            impact=item.impact,
            source=item.source,
            summary=item.summary,
        )
        for item in records
    ]


@router.post("/analyze", response_model=AnalysisResponse)
def analyze(payload: SnapshotInput, db: Session = Depends(get_db)) -> AnalysisResponse:
    engine = AnalysisEngine(db)
    result = engine.analyze(payload)
    engine.save_analysis(payload, result)
    return result


@router.get("/analysis-preview/{symbol}")
def analysis_preview(symbol: str, db: Session = Depends(get_db)) -> dict:
    records = db.scalars(
        select(MarketSnapshot).where(MarketSnapshot.symbol == symbol).order_by(MarketSnapshot.created_at.desc())
    ).all()
    latest = records[0] if records else None
    return {
        "symbol": symbol,
        "latest_score": latest.final_score if latest else 0,
        "latest_decision": latest.decision if latest else "NAO_OPERAR",
        "reasons": summarize_reasons(records),
    }
