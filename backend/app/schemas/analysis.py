from datetime import datetime

from pydantic import BaseModel, Field


class SnapshotInput(BaseModel):
    symbol: str
    market: str = Field(default="FOREX")
    timeframe: str
    open: float
    high: float
    low: float
    close: float
    spread: float
    volume: float = 0.0
    volatility: float
    trend: str
    context_news: str = ""
    timestamp: datetime


class AnalysisResponse(BaseModel):
    symbol: str
    decision: str
    score: float
    technical_score: float
    fundamental_score: float
    historical_score: float
    risk_level: str
    blockers: list[str]
    reasons: list[str]
    indicator_snapshot: dict[str, float | str | bool]


class DashboardSummary(BaseModel):
    total_signals: int
    buy_signals: int
    sell_signals: int
    no_trade_signals: int
    win_rate: float
    best_symbol: str
    best_timeframe: str
    active_alerts: int
    premium_opportunities: int


class OpportunityCard(BaseModel):
    symbol: str
    market: str
    timeframe: str
    score: float
    decision: str
    risk_level: str
    trend: str
    reasons: list[str]


class EconomicEventItem(BaseModel):
    event_time: datetime
    region: str
    title: str
    impact: str
    source: str
    summary: str


class SignalItem(BaseModel):
    id: int
    timestamp: datetime
    symbol: str
    market: str
    timeframe: str
    decision: str
    score: float
    risk_level: str
    trend: str
    reasoning: str


class IntegrationStatus(BaseModel):
    name: str
    category: str
    status: str
    auth_type: str
    base_url: str
    notes: str


class ModuleStatus(BaseModel):
    name: str
    mode: str
    enabled: bool
    description: str


class RiskProfileItem(BaseModel):
    profile_name: str
    stake_percent: float
    daily_stop_percent: float
    daily_target_percent: float
    max_consecutive_losses: int
    cooldown_minutes: int
    observer_mode: bool


class AssetConfigItem(BaseModel):
    symbol: str
    market: str
    provider: str
    priority: int
    enabled: bool
    timeframes: list[str]


class BacktestMetricItem(BaseModel):
    strategy_name: str
    symbol: str
    timeframe: str
    win_rate: float
    payoff: float
    drawdown: float
    net_profit: float
    worst_streak: int
    best_hour: str
    risk_label: str


class ForwardTestMetricItem(BaseModel):
    window_name: str
    signals_count: int
    win_rate: float
    average_score: float
    status: str
    notes: str


class AuditLogItem(BaseModel):
    created_at: datetime
    actor: str
    action: str
    details: str


class UserAccountItem(BaseModel):
    name: str
    email: str
    role: str
    status: str
    two_factor_enabled: bool


class AlertChannelItem(BaseModel):
    name: str
    channel_type: str
    status: str
    destination: str
    notes: str


class SecurityControlItem(BaseModel):
    name: str
    status: str
    severity: str
    details: str


class ScrapingSourceItem(BaseModel):
    name: str
    scope: str
    status: str
    policy: str


class LiveAssetBoardItem(BaseModel):
    symbol: str
    market: str
    timeframe: str
    provider: str
    score: float
    decision: str
    risk_level: str
    trend: str
    spread: float
    volatility: float
    reasons: list[str]
    blockers: list[str]
    indicator_snapshot: dict[str, float | str | bool]


class DashboardPayload(BaseModel):
    summary: DashboardSummary
    opportunities: list[OpportunityCard]
    live_board: list[LiveAssetBoardItem]
    signals: list[SignalItem]
    economic_events: list[EconomicEventItem]
    integrations: list[IntegrationStatus]
    modules: list[ModuleStatus]
    monitored_assets: list[AssetConfigItem]
    risk_profile: RiskProfileItem
    backtests: list[BacktestMetricItem]
    forward_tests: list[ForwardTestMetricItem]
    audits: list[AuditLogItem]
    users: list[UserAccountItem]
    alert_channels: list[AlertChannelItem]
    security_controls: list[SecurityControlItem]
    scraping_sources: list[ScrapingSourceItem]
