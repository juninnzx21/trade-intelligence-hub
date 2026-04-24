from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class MarketSnapshot(Base):
    __tablename__ = "market_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    symbol: Mapped[str] = mapped_column(String(20), index=True)
    market: Mapped[str] = mapped_column(String(20), index=True)
    timeframe: Mapped[str] = mapped_column(String(10), index=True)
    open: Mapped[float] = mapped_column(Float)
    high: Mapped[float] = mapped_column(Float)
    low: Mapped[float] = mapped_column(Float)
    close: Mapped[float] = mapped_column(Float)
    spread: Mapped[float] = mapped_column(Float)
    volume: Mapped[float] = mapped_column(Float, default=0.0)
    volatility: Mapped[float] = mapped_column(Float)
    trend: Mapped[str] = mapped_column(String(20))
    context_news: Mapped[str] = mapped_column(Text, default="")
    technical_score: Mapped[float] = mapped_column(Float)
    fundamental_score: Mapped[float] = mapped_column(Float)
    historical_score: Mapped[float] = mapped_column(Float)
    final_score: Mapped[float] = mapped_column(Float)
    decision: Mapped[str] = mapped_column(String(20), index=True)
    risk_level: Mapped[str] = mapped_column(String(20))
    reasoning: Mapped[str] = mapped_column(Text)
    future_result: Mapped[str] = mapped_column(String(20), default="PENDING")


class EconomicEvent(Base):
    __tablename__ = "economic_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    event_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    region: Mapped[str] = mapped_column(String(20))
    title: Mapped[str] = mapped_column(String(120))
    impact: Mapped[str] = mapped_column(String(20))
    source: Mapped[str] = mapped_column(String(120))
    summary: Mapped[str] = mapped_column(Text)


class RiskRule(Base):
    __tablename__ = "risk_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(60), unique=True)
    threshold: Mapped[float] = mapped_column(Float)
    enabled: Mapped[int] = mapped_column(Integer, default=1)


class IntegrationConfig(Base):
    __tablename__ = "integration_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(60), unique=True)
    category: Mapped[str] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(String(20))
    auth_type: Mapped[str] = mapped_column(String(20))
    base_url: Mapped[str] = mapped_column(String(255))
    notes: Mapped[str] = mapped_column(Text, default="")


class MonitoredAsset(Base):
    __tablename__ = "monitored_assets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    symbol: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    market: Mapped[str] = mapped_column(String(20), index=True)
    provider: Mapped[str] = mapped_column(String(40))
    priority: Mapped[int] = mapped_column(Integer, default=1)
    enabled: Mapped[int] = mapped_column(Integer, default=1)
    timeframes: Mapped[str] = mapped_column(String(80), default="1m,5m,15m,1h")


class SystemModule(Base):
    __tablename__ = "system_modules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(60), unique=True)
    mode: Mapped[str] = mapped_column(String(20))
    enabled: Mapped[int] = mapped_column(Integer, default=1)
    description: Mapped[str] = mapped_column(Text, default="")


class RiskProfile(Base):
    __tablename__ = "risk_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    profile_name: Mapped[str] = mapped_column(String(60), unique=True)
    stake_percent: Mapped[float] = mapped_column(Float, default=1.0)
    daily_stop_percent: Mapped[float] = mapped_column(Float, default=3.0)
    daily_target_percent: Mapped[float] = mapped_column(Float, default=2.0)
    max_consecutive_losses: Mapped[int] = mapped_column(Integer, default=3)
    cooldown_minutes: Mapped[int] = mapped_column(Integer, default=30)
    observer_mode: Mapped[int] = mapped_column(Integer, default=1)


class BacktestMetric(Base):
    __tablename__ = "backtest_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    strategy_name: Mapped[str] = mapped_column(String(60))
    symbol: Mapped[str] = mapped_column(String(20), index=True)
    timeframe: Mapped[str] = mapped_column(String(10), index=True)
    win_rate: Mapped[float] = mapped_column(Float)
    payoff: Mapped[float] = mapped_column(Float)
    drawdown: Mapped[float] = mapped_column(Float)
    net_profit: Mapped[float] = mapped_column(Float)
    worst_streak: Mapped[int] = mapped_column(Integer)
    best_hour: Mapped[str] = mapped_column(String(20))
    risk_label: Mapped[str] = mapped_column(String(20))


class ForwardTestMetric(Base):
    __tablename__ = "forward_test_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    window_name: Mapped[str] = mapped_column(String(60), unique=True)
    signals_count: Mapped[int] = mapped_column(Integer)
    win_rate: Mapped[float] = mapped_column(Float)
    average_score: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(20))
    notes: Mapped[str] = mapped_column(Text, default="")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    actor: Mapped[str] = mapped_column(String(60))
    action: Mapped[str] = mapped_column(String(120))
    details: Mapped[str] = mapped_column(Text, default="")


class UserAccount(Base):
    __tablename__ = "user_accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(80))
    email: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    role: Mapped[str] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(String(20))
    two_factor_enabled: Mapped[int] = mapped_column(Integer, default=0)


class AlertChannel(Base):
    __tablename__ = "alert_channels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(60), unique=True)
    channel_type: Mapped[str] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(String(20))
    destination: Mapped[str] = mapped_column(String(120))
    notes: Mapped[str] = mapped_column(Text, default="")


class SecurityControl(Base):
    __tablename__ = "security_controls"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    status: Mapped[str] = mapped_column(String(20))
    severity: Mapped[str] = mapped_column(String(20))
    details: Mapped[str] = mapped_column(Text, default="")


class ScrapingSource(Base):
    __tablename__ = "scraping_sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    scope: Mapped[str] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(String(20))
    policy: Mapped[str] = mapped_column(Text, default="")
