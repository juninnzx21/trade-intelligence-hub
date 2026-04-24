from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import (
    AuditLog,
    AlertChannel,
    BacktestMetric,
    EconomicEvent,
    ForwardTestMetric,
    IntegrationConfig,
    MarketSnapshot,
    MonitoredAsset,
    RiskProfile,
    ScrapingSource,
    SecurityControl,
    SystemModule,
    UserAccount,
)
from app.schemas.analysis import (
    AssetConfigItem,
    AlertChannelItem,
    AuditLogItem,
    BacktestMetricItem,
    DashboardPayload,
    DashboardSummary,
    EconomicEventItem,
    ForwardTestMetricItem,
    IntegrationStatus,
    ModuleStatus,
    OpportunityCard,
    RiskProfileItem,
    ScrapingSourceItem,
    SecurityControlItem,
    SignalItem,
    UserAccountItem,
)
from app.services.analysis import AnalysisEngine


def build_dashboard_payload(db: Session, persist_live_board: bool = False) -> DashboardPayload:
    summary = build_summary(db)
    opportunities = build_opportunities(db)
    live_board = build_live_board(db, persist=persist_live_board)
    signals = build_signals(db)
    events = build_events(db)
    integrations = [
        IntegrationStatus(
            name=item.name,
            category=item.category,
            status=item.status,
            auth_type=item.auth_type,
            base_url=item.base_url,
            notes=item.notes,
        )
        for item in db.scalars(select(IntegrationConfig).order_by(IntegrationConfig.name.asc())).all()
    ]
    modules = [
        ModuleStatus(name=item.name, mode=item.mode, enabled=bool(item.enabled), description=item.description)
        for item in db.scalars(select(SystemModule).order_by(SystemModule.name.asc())).all()
    ]
    monitored_assets = [
        AssetConfigItem(
            symbol=item.symbol,
            market=item.market,
            provider=item.provider,
            priority=item.priority,
            enabled=bool(item.enabled),
            timeframes=[part.strip() for part in item.timeframes.split(",") if part.strip()],
        )
        for item in db.scalars(select(MonitoredAsset).order_by(MonitoredAsset.priority.asc(), MonitoredAsset.symbol.asc())).all()
    ]
    risk = db.scalars(select(RiskProfile).order_by(RiskProfile.id.asc())).first()
    risk_profile = RiskProfileItem(
        profile_name=risk.profile_name,
        stake_percent=risk.stake_percent,
        daily_stop_percent=risk.daily_stop_percent,
        daily_target_percent=risk.daily_target_percent,
        max_consecutive_losses=risk.max_consecutive_losses,
        cooldown_minutes=risk.cooldown_minutes,
        observer_mode=bool(risk.observer_mode),
    )
    backtests = [
        BacktestMetricItem(
            strategy_name=item.strategy_name,
            symbol=item.symbol,
            timeframe=item.timeframe,
            win_rate=item.win_rate,
            payoff=item.payoff,
            drawdown=item.drawdown,
            net_profit=item.net_profit,
            worst_streak=item.worst_streak,
            best_hour=item.best_hour,
            risk_label=item.risk_label,
        )
        for item in db.scalars(select(BacktestMetric).order_by(BacktestMetric.net_profit.desc())).all()
    ]
    forward_tests = [
        ForwardTestMetricItem(
            window_name=item.window_name,
            signals_count=item.signals_count,
            win_rate=item.win_rate,
            average_score=item.average_score,
            status=item.status,
            notes=item.notes,
        )
        for item in db.scalars(select(ForwardTestMetric).order_by(ForwardTestMetric.signals_count.desc())).all()
    ]
    audits = [
        AuditLogItem(
            created_at=item.created_at,
            actor=item.actor,
            action=item.action,
            details=item.details,
        )
        for item in db.scalars(select(AuditLog).order_by(AuditLog.created_at.desc())).all()[:8]
    ]
    users = [
        UserAccountItem(
            name=item.name,
            email=item.email,
            role=item.role,
            status=item.status,
            two_factor_enabled=bool(item.two_factor_enabled),
        )
        for item in db.scalars(select(UserAccount).order_by(UserAccount.role.asc(), UserAccount.name.asc())).all()
    ]
    alert_channels = [
        AlertChannelItem(
            name=item.name,
            channel_type=item.channel_type,
            status=item.status,
            destination=item.destination,
            notes=item.notes,
        )
        for item in db.scalars(select(AlertChannel).order_by(AlertChannel.name.asc())).all()
    ]
    security_controls = [
        SecurityControlItem(
            name=item.name,
            status=item.status,
            severity=item.severity,
            details=item.details,
        )
        for item in db.scalars(select(SecurityControl).order_by(SecurityControl.name.asc())).all()
    ]
    scraping_sources = [
        ScrapingSourceItem(
            name=item.name,
            scope=item.scope,
            status=item.status,
            policy=item.policy,
        )
        for item in db.scalars(select(ScrapingSource).order_by(ScrapingSource.name.asc())).all()
    ]
    return DashboardPayload(
        summary=summary,
        opportunities=opportunities,
        live_board=live_board,
        signals=signals,
        economic_events=events,
        integrations=integrations,
        modules=modules,
        monitored_assets=monitored_assets,
        risk_profile=risk_profile,
        backtests=backtests,
        forward_tests=forward_tests,
        audits=audits,
        users=users,
        alert_channels=alert_channels,
        security_controls=security_controls,
        scraping_sources=scraping_sources,
    )


def build_summary(db: Session) -> DashboardSummary:
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
    active_alerts = db.scalar(select(func.count()).select_from(EconomicEvent)) or 0
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


def build_opportunities(db: Session) -> list[OpportunityCard]:
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


def build_signals(db: Session) -> list[SignalItem]:
    records = db.scalars(select(MarketSnapshot).order_by(MarketSnapshot.created_at.desc())).all()
    return [
        SignalItem(
            id=item.id,
            timestamp=item.created_at,
            symbol=item.symbol,
            market=item.market,
            timeframe=item.timeframe,
            decision=item.decision,
            score=item.final_score,
            risk_level=item.risk_level,
            trend=item.trend,
            reasoning=item.reasoning,
        )
        for item in records
    ]


def build_events(db: Session) -> list[EconomicEventItem]:
    return [
        EconomicEventItem(
            event_time=item.event_time,
            region=item.region,
            title=item.title,
            impact=item.impact,
            source=item.source,
            summary=item.summary,
        )
        for item in db.scalars(select(EconomicEvent).order_by(EconomicEvent.event_time.asc())).all()
    ]


def build_live_board(db: Session, persist: bool = False):
    engine = AnalysisEngine(db)
    board: list = []
    assets = db.scalars(select(MonitoredAsset).where(MonitoredAsset.enabled == 1).order_by(MonitoredAsset.priority.asc())).all()
    for asset in assets:
        timeframe = [part.strip() for part in asset.timeframes.split(",") if part.strip()][0]
        analysis = engine.analyze_live_asset(asset.symbol, asset.market, timeframe, persist=persist)
        board.append(
            {
                "symbol": asset.symbol,
                "market": asset.market,
                "timeframe": timeframe,
                "provider": asset.provider,
                "score": analysis.score,
                "decision": analysis.decision,
                "risk_level": analysis.risk_level,
                "trend": str(analysis.indicator_snapshot["trend_primary"]),
                "spread": float(analysis.indicator_snapshot["spread"]),
                "volatility": float(analysis.indicator_snapshot["volatility_pct"]),
                "reasons": analysis.reasons,
                "blockers": analysis.blockers,
                "indicator_snapshot": analysis.indicator_snapshot,
            }
        )
    return sorted(board, key=lambda item: item["score"], reverse=True)
