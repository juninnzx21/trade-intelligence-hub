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
