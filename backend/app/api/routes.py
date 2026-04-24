from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.db.models import MarketSnapshot
from app.schemas.analysis import AnalysisResponse, DashboardPayload, EconomicEventItem, OpportunityCard, SnapshotInput
from app.services.analysis import AnalysisEngine, summarize_reasons
from app.services.dashboard import build_dashboard_payload, build_events, build_live_board, build_opportunities, build_signals, build_summary

router = APIRouter()


@router.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/dashboard", response_model=DashboardPayload)
def dashboard(db: Session = Depends(get_db)) -> DashboardPayload:
    return build_dashboard_payload(db)


@router.get("/dashboard/summary")
def dashboard_summary(db: Session = Depends(get_db)):
    return build_summary(db)


@router.get("/signals")
def list_signals(db: Session = Depends(get_db)) -> list[dict]:
    return [item.model_dump() for item in build_signals(db)]


@router.get("/opportunities")
def opportunities(db: Session = Depends(get_db)) -> list[OpportunityCard]:
    return build_opportunities(db)


@router.get("/economic-events")
def economic_events(db: Session = Depends(get_db)) -> list[EconomicEventItem]:
    return build_events(db)


@router.get("/market/live-board")
def live_board(db: Session = Depends(get_db)):
    return build_live_board(db, persist=False)


@router.post("/market/live-board/refresh")
def refresh_live_board(db: Session = Depends(get_db)):
    return build_live_board(db, persist=True)


@router.get("/admin/overview")
def admin_overview(db: Session = Depends(get_db)):
    dashboard = build_dashboard_payload(db)
    return {
        "integrations": [item.model_dump() for item in dashboard.integrations],
        "modules": [item.model_dump() for item in dashboard.modules],
        "monitored_assets": [item.model_dump() for item in dashboard.monitored_assets],
        "risk_profile": dashboard.risk_profile.model_dump(),
        "audits": [item.model_dump() for item in dashboard.audits],
        "users": [item.model_dump() for item in dashboard.users],
        "alert_channels": [item.model_dump() for item in dashboard.alert_channels],
        "security_controls": [item.model_dump() for item in dashboard.security_controls],
        "scraping_sources": [item.model_dump() for item in dashboard.scraping_sources],
    }


@router.get("/backtest/overview")
def backtest_overview(db: Session = Depends(get_db)):
    return [item.model_dump() for item in build_dashboard_payload(db).backtests]


@router.get("/forward-test/overview")
def forward_test_overview(db: Session = Depends(get_db)):
    return [item.model_dump() for item in build_dashboard_payload(db).forward_tests]


@router.get("/reports/export")
def export_report(db: Session = Depends(get_db)):
    return build_dashboard_payload(db).model_dump()


@router.get("/reports/export.csv", response_class=PlainTextResponse)
def export_report_csv(db: Session = Depends(get_db)):
    payload = build_dashboard_payload(db)
    lines = [
        "section,name,value,extra",
        f"summary,total_signals,{payload.summary.total_signals},-",
        f"summary,win_rate,{payload.summary.win_rate},-",
        f"summary,best_symbol,{payload.summary.best_symbol},{payload.summary.best_timeframe}",
    ]
    for item in payload.live_board:
        lines.append(f"live_board,{item.symbol},{item.score},{item.decision}")
    for item in payload.backtests:
        lines.append(f"backtest,{item.strategy_name},{item.net_profit},{item.win_rate}")
    return "\n".join(lines)


@router.post("/analyze", response_model=AnalysisResponse)
def analyze(payload: SnapshotInput, db: Session = Depends(get_db)) -> AnalysisResponse:
    engine = AnalysisEngine(db)
    result = engine.analyze(payload)
    engine.save_analysis(payload, result)
    return result


@router.get("/analysis-preview/{symbol}")
def analysis_preview(symbol: str, db: Session = Depends(get_db)) -> dict:
    records = db.query(MarketSnapshot).filter(MarketSnapshot.symbol == symbol).order_by(MarketSnapshot.created_at.desc()).all()
    latest = records[0] if records else None
    return {
        "symbol": symbol,
        "latest_score": latest.final_score if latest else 0,
        "latest_decision": latest.decision if latest else "NAO_OPERAR",
        "reasons": summarize_reasons(records),
    }
