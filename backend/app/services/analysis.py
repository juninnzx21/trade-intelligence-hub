from __future__ import annotations

from collections.abc import Sequence
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import log_event
from app.core.time import utc_now
from app.db.models import (
    AlertChannel,
    ApiConnection,
    Asset,
    AuditLog,
    BacktestMetric,
    CandleRecord,
    DecisionSignal,
    EconomicEvent,
    ForwardTestMetric,
    IndicatorRecord,
    IntegrationConfig,
    MarketNews,
    MarketSnapshot,
    MonitoredAsset,
    RiskProfile,
    RiskRule,
    ScrapingSource,
    SecurityControl,
    SignalResult,
    StrategyRule,
    SystemLog,
    SystemModule,
    UserAccount,
)
from app.schemas.analysis import AnalysisResponse, SnapshotInput
from app.services.engines.fundamental_engine import calculate_fundamental_score
from app.services.engines.historical_engine import calculate_historical_score
from app.services.engines.risk_engine import adjust_for_validation
from app.services.engines.scoring_engine import calculate_final_score, decision_from_score, risk_level_from_context
from app.services.engines.signal_timing_engine import build_signal_timing
from app.services.engines.signal_validation_engine import validate_signal
from app.services.engines.technical_engine import calculate_technical_score
from app.services.market_data import Candle, MarketDataService, calculate_indicator_snapshot


class AnalysisEngine:
    def __init__(self, db: Session):
        self.db = db
        self.market_data = MarketDataService(db)

    def analyze(self, payload: SnapshotInput, indicator_snapshot: dict[str, float | str | bool] | None = None) -> AnalysisResponse:
        snapshot = indicator_snapshot or self._indicator_snapshot_from_payload(payload)
        technical = calculate_technical_score(payload, snapshot)
        fundamental = calculate_fundamental_score(self.db, payload)
        historical = calculate_historical_score(self.db, payload, snapshot)
        timing = build_signal_timing(payload)
        validation = validate_signal(self.db, payload, snapshot, timing)

        final_score = calculate_final_score(technical.score, fundamental.score, historical.score)
        final_score = adjust_for_validation(final_score, validation)
        reasons = technical.reasons + fundamental.reasons + historical.reasons
        decision = "NAO_OPERAR" if validation.blockers else decision_from_score(final_score, payload.trend)
        risk_level = "Alto" if validation.blockers else risk_level_from_context(final_score, payload.volatility, payload.spread)

        if decision == "NAO_OPERAR":
            timing.entry_time = None
            timing.exit_time = None
            timing.duration_minutes = None
            timing.duration_label = None
            timing.duration_reason = None
            timing.signal_valid_until = None

        return AnalysisResponse(
            symbol=payload.symbol,
            timeframe=payload.timeframe,
            decision=decision,
            score=final_score,
            technical_score=technical.score,
            fundamental_score=fundamental.score,
            historical_score=historical.score,
            risk_level=risk_level,
            entry_time=timing.entry_time,
            exit_time=timing.exit_time,
            duration=timing.duration_label,
            duration_minutes=timing.duration_minutes,
            duration_reason=timing.duration_reason,
            signal_valid_until=timing.signal_valid_until,
            technical_reasons=technical.reasons[:5],
            fundamental_reasons=(fundamental.reasons + historical.reasons + validation.warnings)[:6],
            block_reasons=validation.blockers,
            reasons=reasons[:8],
            warning="Sinal apenas para analise. Nao executa ordens reais.",
            indicator_snapshot=snapshot,
        )

    def save_analysis(self, payload: SnapshotInput, analysis: AnalysisResponse) -> MarketSnapshot:
        snapshot = MarketSnapshot(
            created_at=payload.timestamp,
            symbol=payload.symbol,
            market=payload.market,
            timeframe=payload.timeframe,
            open=payload.open,
            high=payload.high,
            low=payload.low,
            close=payload.close,
            spread=payload.spread,
            volume=payload.volume,
            volatility=payload.volatility,
            trend=payload.trend,
            context_news=payload.context_news,
            technical_score=analysis.technical_score,
            fundamental_score=analysis.fundamental_score,
            historical_score=analysis.historical_score,
            final_score=analysis.score,
            decision=analysis.decision,
            risk_level=analysis.risk_level,
            reasoning=" | ".join(analysis.reasons + analysis.block_reasons),
        )
        self.db.add(snapshot)
        self.db.add(
            CandleRecord(
                asset=payload.symbol,
                timeframe=payload.timeframe,
                source=payload.market,
                timestamp=payload.timestamp,
                open=payload.open,
                high=payload.high,
                low=payload.low,
                close=payload.close,
                spread=payload.spread,
                volume=payload.volume,
            )
        )
        self.db.add(
            IndicatorRecord(
                asset=payload.symbol,
                timeframe=payload.timeframe,
                timestamp=payload.timestamp,
                trend=payload.trend,
                rsi=float(analysis.indicator_snapshot["rsi"]),
                macd=float(analysis.indicator_snapshot["macd"]),
                atr=float(analysis.indicator_snapshot["atr"]),
                vwap=float(analysis.indicator_snapshot["vwap"]),
                volatility=float(analysis.indicator_snapshot["volatility_pct"]),
                summary=" | ".join(analysis.technical_reasons[:3]),
            )
        )
        signal = DecisionSignal(
            asset=payload.symbol,
            market=payload.market,
            timeframe=payload.timeframe,
            decision=analysis.decision,
            score=analysis.score,
            risk=analysis.risk_level,
            entry_time=analysis.entry_time,
            exit_time=analysis.exit_time,
            signal_valid_until=analysis.signal_valid_until,
            duration_minutes=analysis.duration_minutes,
            technical_reasons=" | ".join(analysis.technical_reasons),
            fundamental_reasons=" | ".join(analysis.fundamental_reasons),
            block_reasons=" | ".join(analysis.block_reasons),
            warning=analysis.warning,
            created_at=payload.timestamp,
        )
        self.db.add(signal)
        self.db.add(
            AuditLog(
                created_at=utc_now(),
                actor="system",
                action=f"signal:{analysis.decision}",
                details=f"{payload.symbol} {payload.timeframe} score={analysis.score}",
            )
        )
        self.db.add(
            SystemLog(
                created_at=utc_now(),
                level="INFO",
                module="analysis_engine",
                message=f"{payload.symbol} {payload.timeframe} -> {analysis.decision} score={analysis.score}",
            )
        )
        self.db.commit()
        self.db.refresh(snapshot)
        persisted_signal = self.db.scalars(
            select(DecisionSignal)
            .where(DecisionSignal.asset == payload.symbol, DecisionSignal.timeframe == payload.timeframe)
            .order_by(DecisionSignal.id.desc())
        ).first()
        if persisted_signal:
            self.db.add(
                SignalResult(
                    signal_id=persisted_signal.id,
                    status="open" if analysis.decision != "NAO_OPERAR" else "blocked",
                    evaluated_at=None,
                    outcome_label="PENDING",
                    pnl_units=0.0,
                    notes="Forward test observer mode.",
                )
            )
            self.db.commit()
        log_event(
            "info",
            "analysis_saved",
            asset=payload.symbol,
            timeframe=payload.timeframe,
            decision=analysis.decision,
            score=analysis.score,
        )
        return snapshot

    def analyze_live_asset(self, symbol: str, market: str, timeframe: str, persist: bool = False) -> AnalysisResponse:
        candles, _provider = self.market_data.get_series(symbol, market, timeframe, 120)
        spread = self.market_data.get_current_spread(symbol, market)
        indicator_snapshot = calculate_indicator_snapshot(candles, spread)
        latest = candles[-1]
        payload = SnapshotInput(
            symbol=symbol,
            market=market,
            timeframe=timeframe,
            open=latest.open,
            high=latest.high,
            low=latest.low,
            close=latest.close,
            spread=spread,
            volume=latest.volume,
            volatility=float(indicator_snapshot["volatility_pct"]),
            trend=str(indicator_snapshot["trend_primary"]),
            context_news=self._build_news_context(symbol),
            timestamp=latest.timestamp,
        )
        analysis = self.analyze(payload, indicator_snapshot=indicator_snapshot)
        if persist:
            self.save_analysis(payload, analysis)
        return analysis

    def _indicator_snapshot_from_payload(self, payload: SnapshotInput) -> dict[str, float | str | bool]:
        candles = self.market_data._generate_demo_series(payload.symbol, payload.market, payload.timeframe, 100)
        candles[-1] = Candle(
            timestamp=payload.timestamp,
            open=payload.open,
            high=payload.high,
            low=payload.low,
            close=payload.close,
            volume=payload.volume,
        )
        return calculate_indicator_snapshot(candles, payload.spread)

    def _build_news_context(self, symbol: str) -> str:
        events = self.db.scalars(
            select(EconomicEvent).where(EconomicEvent.event_time >= utc_now() - timedelta(hours=1))
        ).all()
        news = self.db.scalars(
            select(MarketNews).where(MarketNews.asset_scope.in_([symbol, "GLOBAL"])).order_by(MarketNews.published_at.desc())
        ).all()
        latest_asset = self.db.scalars(
            select(MarketSnapshot).where(MarketSnapshot.symbol == symbol).order_by(MarketSnapshot.created_at.desc())
        ).first()
        event_titles = ", ".join(event.title for event in events[:2])
        news_titles = ", ".join(item.title for item in news[:2])
        base_context = latest_asset.context_news if latest_asset else "Sem manchete critica imediata."
        return f"{base_context} {event_titles} {news_titles}".strip()


def summarize_reasons(records: Sequence[MarketSnapshot]) -> list[str]:
    if not records:
        return ["Sem leitura suficiente para gerar explicacoes."]
    top = sorted(records, key=lambda item: item.final_score, reverse=True)[0]
    return [part.strip() for part in top.reasoning.split("|") if part.strip()][:4]


def seed_demo_dataset(db: Session) -> None:
    base_time = utc_now().replace(minute=0, second=0, microsecond=0)
    if not db.scalars(select(MarketSnapshot)).first():
        for sample in [
            {
                "created_at": base_time - timedelta(minutes=15),
                "symbol": "EUR/USD",
                "market": "FOREX",
                "timeframe": "15m",
                "open": 1.0832,
                "high": 1.0846,
                "low": 1.0827,
                "close": 1.0843,
                "spread": 0.7,
                "volume": 12000,
                "volatility": 1.2,
                "trend": "alta",
                "context_news": "Sem FOMC no curto prazo, dolar com fluxo misto.",
                "technical_score": 82,
                "fundamental_score": 68,
                "historical_score": 74,
                "final_score": 76.4,
                "decision": "COMPRA",
                "risk_level": "Moderado",
                "reasoning": "Tendencia primaria de alta confirmada. | Spread favoravel para execucao. | Historico semelhante positivo.",
                "future_result": "WIN",
            },
            {
                "created_at": base_time - timedelta(minutes=10),
                "symbol": "BTC/USDT",
                "market": "CRYPTO",
                "timeframe": "5m",
                "open": 68210,
                "high": 68340,
                "low": 68080,
                "close": 68125,
                "spread": 1.8,
                "volume": 8900,
                "volatility": 2.8,
                "trend": "lateral",
                "context_news": "Mercado aguarda dado de inflacao dos EUA.",
                "technical_score": 49,
                "fundamental_score": 44,
                "historical_score": 55,
                "final_score": 49.4,
                "decision": "NAO_OPERAR",
                "risk_level": "Alto",
                "reasoning": "Estrutura tecnica sem direcao limpa. | Agenda economica carregada com evento de alto impacto. | Mercado em lateralizacao extrema.",
                "future_result": "NEUTRAL",
            },
            {
                "created_at": base_time - timedelta(minutes=5),
                "symbol": "GBP/USD",
                "market": "FOREX",
                "timeframe": "1h",
                "open": 1.2690,
                "high": 1.2696,
                "low": 1.2641,
                "close": 1.2648,
                "spread": 1.0,
                "volume": 15020,
                "volatility": 2.0,
                "trend": "baixa",
                "context_news": "Banco central mais hawkish e dados de atividade fracos.",
                "technical_score": 79,
                "fundamental_score": 61,
                "historical_score": 70,
                "final_score": 72.35,
                "decision": "VENDA",
                "risk_level": "Moderado",
                "reasoning": "Tendencia primaria de baixa confirmada. | Pressao vendedora consistente no candle. | Historico semelhante positivo.",
                "future_result": "WIN",
            },
        ]:
            db.add(MarketSnapshot(**sample))

    if not db.scalars(select(EconomicEvent)).first():
        for event in [
            EconomicEvent(
                event_time=base_time + timedelta(hours=1),
                region="US",
                title="Payroll",
                impact="ALTO",
                source="Calendario Economico Publico",
                summary="Divulgacao do payroll com potencial de elevar a volatilidade em pares dolarizados.",
            ),
            EconomicEvent(
                event_time=base_time + timedelta(hours=4),
                region="EU",
                title="Fala de dirigente do BCE",
                impact="MEDIO",
                source="Noticias Financeiras Publicas",
                summary="Declaracoes monitoradas para impacto em EUR crosses.",
            ),
        ]:
            db.add(event)

    if not db.scalars(select(MarketNews)).first():
        for item in [
            MarketNews(
                published_at=base_time - timedelta(minutes=20),
                title="Dolar opera estavel antes do payroll",
                impact="MEDIO",
                asset_scope="GLOBAL",
                source="Noticias Financeiras Publicas",
                summary="Fluxo defensivo moderado antes de dado macro importante.",
            ),
            MarketNews(
                published_at=base_time - timedelta(minutes=12),
                title="Bitcoin absorve realizacao e mantem estrutura de alta",
                impact="MEDIO",
                asset_scope="BTC/USDT",
                source="Noticias Financeiras Publicas",
                summary="Mercado cripto mantem apetite a risco sem evento extremo imediato.",
            ),
        ]:
            db.add(item)

    if not db.scalars(select(RiskRule)).first():
        for rule in [
            RiskRule(name="max_spread", threshold=2.5, enabled=1),
            RiskRule(name="max_volatility", threshold=4.2, enabled=1),
            RiskRule(name="max_negative_streak", threshold=3, enabled=1),
        ]:
            db.add(rule)

    if not db.scalars(select(IntegrationConfig)).first():
        for integration in [
            IntegrationConfig(
                name="Binance",
                category="Mercado",
                status="ativo",
                auth_type="publica",
                base_url="https://api.binance.com",
                notes="Klines e spread publico disponiveis para cripto.",
            ),
            IntegrationConfig(
                name="OANDA",
                category="Mercado",
                status="aguardando-chave",
                auth_type="api-key",
                base_url="https://api-fxpractice.oanda.com",
                notes="Estrutura pronta para forex oficial quando a chave for configurada.",
            ),
            IntegrationConfig(
                name="Calendario Economico Publico",
                category="Macro",
                status="observador",
                auth_type="publica",
                base_url="https://www.forexfactory.com/calendar",
                notes="Uso apenas para fontes publicas permitidas e sem bypass de login.",
            ),
        ]:
            db.add(integration)

    if not db.scalars(select(ApiConnection)).first():
        for connection in [
            ApiConnection(name="oanda-demo", provider="OANDA", mode="demo", status="ready-for-env", base_url="https://api-fxpractice.oanda.com", notes="Conta demo v20."),
            ApiConnection(name="binance-public", provider="Binance", mode="public", status="active", base_url="https://api.binance.com", notes="Klines, ticker e book ticker publicos."),
        ]:
            db.add(connection)

    if not db.scalars(select(MonitoredAsset)).first():
        for asset in [
            MonitoredAsset(symbol="EUR/USD", market="FOREX", provider="OANDA-ready", priority=1, enabled=1, timeframes="1m,5m,15m,1h"),
            MonitoredAsset(symbol="GBP/USD", market="FOREX", provider="OANDA-ready", priority=1, enabled=1, timeframes="5m,15m,1h"),
            MonitoredAsset(symbol="BTC/USDT", market="CRYPTO", provider="Binance", priority=1, enabled=1, timeframes="1m,5m,15m,1h"),
            MonitoredAsset(symbol="ETH/USDT", market="CRYPTO", provider="Binance", priority=2, enabled=1, timeframes="5m,15m,1h"),
        ]:
            db.add(asset)

    if not db.scalars(select(Asset)).first():
        for asset in [
            Asset(symbol="EUR/USD", market="FOREX", source="OANDA", enabled=1),
            Asset(symbol="GBP/USD", market="FOREX", source="OANDA", enabled=1),
            Asset(symbol="BTC/USDT", market="CRYPTO", source="Binance", enabled=1),
            Asset(symbol="ETH/USDT", market="CRYPTO", source="Binance", enabled=1),
        ]:
            db.add(asset)

    if not db.scalars(select(SystemModule)).first():
        for module in [
            SystemModule(name="Data Collector", mode="observer", enabled=1, description="Coleta snapshots, contexto e eventos."),
            SystemModule(name="Technical Engine", mode="active", enabled=1, description="Calcula indicadores, estrutura e momentum."),
            SystemModule(name="Macro Engine", mode="observer", enabled=1, description="Agenda economica e manchetes publicas."),
            SystemModule(name="Backtest Lab", mode="active", enabled=1, description="Avalia estrategia por ativo, horario e timeframe."),
            SystemModule(name="Forward Test", mode="observer", enabled=1, description="Registra sinais ao vivo sem executar ordens."),
            SystemModule(name="Execution Bridge", mode="disabled", enabled=0, description="Mantido desligado ate validacao estatistica futura."),
        ]:
            db.add(module)

    if not db.scalars(select(RiskProfile)).first():
        db.add(
            RiskProfile(
                profile_name="default-observer",
                stake_percent=0.8,
                daily_stop_percent=2.5,
                daily_target_percent=1.8,
                max_consecutive_losses=3,
                cooldown_minutes=45,
                observer_mode=1,
            )
        )

    if not db.scalars(select(BacktestMetric)).first():
        for metric in [
            BacktestMetric(
                strategy_name="Trend + Pullback + Macro Filter",
                symbol="EUR/USD",
                timeframe="15m",
                win_rate=62.4,
                payoff=1.48,
                drawdown=7.2,
                net_profit=18.6,
                worst_streak=4,
                best_hour="10:00 UTC",
                risk_label="Moderado",
            ),
            BacktestMetric(
                strategy_name="Breakout + VWAP + Sentiment",
                symbol="BTC/USDT",
                timeframe="5m",
                win_rate=58.3,
                payoff=1.61,
                drawdown=10.8,
                net_profit=26.2,
                worst_streak=5,
                best_hour="13:00 UTC",
                risk_label="Moderado",
            ),
        ]:
            db.add(metric)

    if not db.scalars(select(ForwardTestMetric)).first():
        for metric in [
            ForwardTestMetric(
                window_name="30d observer",
                signals_count=512,
                win_rate=57.9,
                average_score=68.4,
                status="validando",
                notes="Base minima de 500 sinais atingida em ambiente sem dinheiro.",
            ),
            ForwardTestMetric(
                window_name="7d quality pulse",
                signals_count=119,
                win_rate=60.5,
                average_score=71.2,
                status="em_coleta",
                notes="Concentrando apenas leituras acima de 66 pontos.",
            ),
        ]:
            db.add(metric)

    if not db.scalars(select(StrategyRule)).first():
        for rule in [
            StrategyRule(name="trend_pullback", category="technical", enabled=1, config_summary="Trend + pullback + volume + sem noticia forte."),
            StrategyRule(name="breakout_vwap", category="technical", enabled=1, config_summary="Rompimento com VWAP e momentum controlado."),
            StrategyRule(name="macro_blocker", category="fundamental", enabled=1, config_summary="Bloqueia entrada perto de evento de alto impacto."),
        ]:
            db.add(rule)

    if not db.scalars(select(AuditLog)).first():
        for audit in [
            AuditLog(created_at=base_time - timedelta(minutes=42), actor="system", action="seed:dataset", details="Carga inicial do observador."),
            AuditLog(created_at=base_time - timedelta(minutes=19), actor="system", action="backtest:refresh", details="Metricas recalculadas por estrategia."),
        ]:
            db.add(audit)

    if not db.scalars(select(UserAccount)).first():
        for user in [
            UserAccount(name="Admin Operator", email="admin@tradehub.local", role="admin", status="active", two_factor_enabled=1),
            UserAccount(name="Risk Analyst", email="risk@tradehub.local", role="analyst", status="active", two_factor_enabled=1),
            UserAccount(name="Observer Seat", email="observer@tradehub.local", role="viewer", status="pilot", two_factor_enabled=0),
        ]:
            db.add(user)

    if not db.scalars(select(AlertChannel)).first():
        for channel in [
            AlertChannel(name="Telegram Ops", channel_type="telegram", status="planned", destination="@trade_ops", notes="Pronto para fase de alertas."),
            AlertChannel(name="WhatsApp Desk", channel_type="whatsapp", status="planned", destination="+55-00-0000-0000", notes="Somente notificacao, nunca promessa de ganho."),
            AlertChannel(name="Mobile Push", channel_type="push", status="observer", destination="ios/android", notes="Usado para sinais fortes e bloqueios macro."),
        ]:
            db.add(channel)

    if not db.scalars(select(SecurityControl)).first():
        for control in [
            SecurityControl(name="API keys encryption", status="designed", severity="high", details="Chaves ficam preparadas para criptografia em repouso."),
            SecurityControl(name="Audit logging", status="active", severity="high", details="Acoes do motor e do admin sao registradas."),
            SecurityControl(name="2FA optional", status="planned", severity="medium", details="Usuarios premium podem exigir segundo fator."),
            SecurityControl(name="Backup policy", status="planned", severity="medium", details="Backups diarios em VPS/Linux no roadmap operacional."),
        ]:
            db.add(control)

    if not db.scalars(select(ScrapingSource)).first():
        for source in [
            ScrapingSource(name="Economic Calendar", scope="macro", status="observer", policy="Somente pagina publica, sem login, captcha ou bypass."),
            ScrapingSource(name="Financial Headlines", scope="news", status="observer", policy="Manchetes publicas e metadata de impacto apenas."),
            ScrapingSource(name="Central Bank Statements", scope="macro", status="planned", policy="Captura de comunicados publicos oficiais."),
        ]:
            db.add(source)

    if not db.scalars(select(SystemLog)).first():
        db.add(SystemLog(created_at=base_time - timedelta(minutes=30), level="INFO", module="bootstrap", message="Sistema iniciado em modo observador."))

    db.commit()
