from collections.abc import Sequence
from datetime import UTC, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    ApiConnection,
    Asset,
    AuditLog,
    AlertChannel,
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
from app.services.market_data import Candle, MarketDataService, calculate_indicator_snapshot


TIMEFRAME_TO_MINUTES = {"1m": 1, "5m": 5, "15m": 15, "1h": 60}


class AnalysisEngine:
    def __init__(self, db: Session):
        self.db = db
        self.market_data = MarketDataService(db)

    def analyze(self, payload: SnapshotInput, indicator_snapshot: dict[str, float | str | bool] | None = None) -> AnalysisResponse:
        snapshot = indicator_snapshot or self._indicator_snapshot_from_payload(payload)
        blockers = self._evaluate_blockers(payload, snapshot)
        technical_score, technical_reasons = self._technical_score(payload, snapshot)
        fundamental_score, fundamental_reasons = self._fundamental_score(payload)
        historical_score, historical_reasons = self._historical_score(payload, snapshot)

        final_score = round((technical_score * 0.45) + (fundamental_score * 0.25) + (historical_score * 0.30), 2)
        reasons = technical_reasons + fundamental_reasons + historical_reasons
        entry_time, exit_time, duration_minutes, duration_reason, valid_until = self._signal_timing(payload)

        if blockers:
            final_score = min(final_score, 50)
            decision = "NAO_OPERAR"
            risk_level = "Alto"
            entry_time = None
            exit_time = None
            duration_minutes = None
            duration_reason = None
            valid_until = None
        else:
            decision = self._decision_from_score(final_score, payload.trend)
            risk_level = self._risk_level(final_score, payload.volatility, payload.spread)
            if decision == "NAO_OPERAR":
                entry_time = None
                exit_time = None
                duration_minutes = None
                duration_reason = None
                valid_until = None

        return AnalysisResponse(
            symbol=payload.symbol,
            timeframe=payload.timeframe,
            decision=decision,
            score=final_score,
            technical_score=technical_score,
            fundamental_score=fundamental_score,
            historical_score=historical_score,
            risk_level=risk_level,
            entry_time=entry_time,
            exit_time=exit_time,
            duration=f"{duration_minutes} minutos" if duration_minutes and duration_minutes < 60 else ("1 hora" if duration_minutes == 60 else None),
            duration_minutes=duration_minutes,
            duration_reason=duration_reason,
            signal_valid_until=valid_until,
            technical_reasons=technical_reasons[:5],
            fundamental_reasons=(fundamental_reasons + historical_reasons)[:5],
            block_reasons=blockers,
            reasons=reasons[:6],
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
                created_at=datetime.now(UTC),
                actor="system",
                action=f"signal:{analysis.decision}",
                details=f"{payload.symbol} {payload.timeframe} score={analysis.score}",
            )
        )
        self.db.add(
            SystemLog(
                created_at=datetime.now(UTC),
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

    def _signal_timing(self, payload: SnapshotInput) -> tuple[datetime, datetime, int, str, datetime]:
        minutes = TIMEFRAME_TO_MINUTES.get(payload.timeframe, 5)
        candle_open = payload.timestamp.astimezone(UTC).replace(second=0, microsecond=0)
        now = datetime.now(UTC).replace(second=0, microsecond=0)
        entry_time = candle_open + timedelta(minutes=minutes)
        advanced_limit = candle_open + timedelta(minutes=max(1, int(minutes * 0.6)))
        if now > advanced_limit:
            entry_time = candle_open + timedelta(minutes=minutes)
        if entry_time <= now:
            entry_time = entry_time + timedelta(minutes=minutes)
        exit_time = entry_time + timedelta(minutes=minutes)
        valid_until = entry_time + timedelta(minutes=1 if minutes <= 5 else 2 if minutes == 15 else 5)
        duration_reason = (
            "Duracao alinhada ao timeframe e ao fechamento do proximo ciclo valido."
            if minutes < 60
            else "Duracao mais longa porque a leitura usa estrutura de 1 hora."
        )
        return entry_time, exit_time, minutes, duration_reason, valid_until

    def _evaluate_blockers(self, payload: SnapshotInput, snapshot: dict[str, float | str | bool]) -> list[str]:
        blockers: list[str] = []
        if payload.spread > 2.5:
            blockers.append("Spread elevado para o contexto atual.")
        if payload.volatility > 4.2:
            blockers.append("Volatilidade anormal detectada.")
        if "FOMC" in payload.context_news.upper() or "PAYROLL" in payload.context_news.upper():
            blockers.append("Noticia macro de alto impacto muito proxima.")
        candle_range = payload.high - payload.low
        body = abs(payload.close - payload.open)
        if candle_range and body / candle_range > 0.85:
            blockers.append("Candle excessivamente esticado.")
        if payload.trend.lower() == "lateral" and payload.volatility < 0.5:
            blockers.append("Mercado em lateralizacao extrema.")
        if bool(snapshot["lateral"]):
            blockers.append("Mercado sem direcao clara.")
        recent = self.db.scalars(
            select(MarketSnapshot).where(MarketSnapshot.symbol == payload.symbol).order_by(MarketSnapshot.created_at.desc())
        ).all()[:6]
        negative_streak = 0
        for item in recent:
            if item.future_result.upper() in {"LOSS", "NEGATIVE"}:
                negative_streak += 1
            else:
                break
        if negative_streak >= 3:
            blockers.append("Sequencia ruim recente para o ativo.")
        return blockers

    def _technical_score(self, payload: SnapshotInput, snapshot: dict[str, float | str | bool]) -> tuple[float, list[str]]:
        score = 48.0
        reasons: list[str] = []
        body = payload.close - payload.open
        amplitude = max(payload.high - payload.low, 0.0001)

        if str(snapshot["trend_primary"]).lower() in {"alta", "bullish"}:
            score += 12
            reasons.append("Tendencia primaria de alta confirmada.")
        elif str(snapshot["trend_primary"]).lower() in {"baixa", "bearish"}:
            score += 12
            reasons.append("Tendencia primaria de baixa confirmada.")
        else:
            score -= 8
            reasons.append("Estrutura tecnica sem direcao limpa.")

        if str(snapshot["trend_secondary"]) == str(snapshot["trend_primary"]) and str(snapshot["trend_primary"]) != "lateral":
            score += 8
            reasons.append("Tendencia secundaria confirma a direcao principal.")

        if body > 0 and payload.close > (payload.low + amplitude * 0.65):
            score += 8
            reasons.append("Fechamento forte perto da maxima.")
        elif body < 0 and payload.close < (payload.low + amplitude * 0.35):
            score += 8
            reasons.append("Pressao vendedora consistente no candle.")

        if 0.6 <= payload.volatility <= 2.4:
            score += 10
            reasons.append("Volatilidade operacional saudavel.")
        else:
            score -= 6
            reasons.append("Volatilidade fora da faixa ideal.")

        rsi = float(snapshot["rsi"])
        if 48 <= rsi <= 66 and str(snapshot["trend_primary"]) == "alta":
            score += 8
            reasons.append("RSI sustenta continuidade sem exaustao.")
        elif 34 <= rsi <= 52 and str(snapshot["trend_primary"]) == "baixa":
            score += 8
            reasons.append("RSI confirma dominancia vendedora sem saturacao.")
        elif rsi > 75 or rsi < 25:
            score -= 8
            reasons.append("RSI em zona de exaustao eleva risco de reversao.")

        if float(snapshot["macd"]) > float(snapshot["macd_signal"]) and str(snapshot["trend_primary"]) == "alta":
            score += 7
            reasons.append("MACD acima do sinal reforca momentum comprador.")
        elif float(snapshot["macd"]) < float(snapshot["macd_signal"]) and str(snapshot["trend_primary"]) == "baixa":
            score += 7
            reasons.append("MACD abaixo do sinal reforca momentum vendedor.")

        if bool(snapshot["breakout"]):
            score += 6
            reasons.append("Preco testa rompimento de estrutura relevante.")
        if bool(snapshot["pullback"]):
            score += 5
            reasons.append("Pullback tecnico oferece ponto mais limpo.")
        if bool(snapshot["lateral"]):
            score -= 10

        if float(snapshot["candle_strength"]) >= 0.68:
            score += 4
            reasons.append("Forca do candle favorece continuacao.")

        pattern = str(snapshot["pattern"])
        if pattern in {"engolfo_de_alta", "engolfo_de_baixa"}:
            score += 5
            reasons.append(f"Padrao de candle relevante detectado: {pattern}.")

        momentum_pct = float(snapshot["momentum_pct"])
        if 0.12 <= abs(momentum_pct) <= 1.8:
            score += 4
            reasons.append("Momentum equilibrado para continuidade.")
        elif abs(momentum_pct) > 2.8:
            score -= 5
            reasons.append("Momentum excessivo sugere movimento esticado.")

        if payload.volume > 0:
            if payload.volume >= 10000:
                score += 6
                reasons.append("Volume reforca o movimento.")
            else:
                score -= 3
                reasons.append("Volume ainda sem conviccao.")

        if payload.spread <= 1.0:
            score += 6
            reasons.append("Spread favoravel para execucao.")
        else:
            score -= min(payload.spread * 3, 10)

        return max(0.0, min(round(score, 2), 100.0)), reasons

    def _fundamental_score(self, payload: SnapshotInput) -> tuple[float, list[str]]:
        score = 55.0
        reasons: list[str] = []
        now = payload.timestamp.astimezone(timezone.utc)
        window_start = now - timedelta(hours=2)
        window_end = now + timedelta(hours=3)
        events = self.db.scalars(
            select(EconomicEvent).where(EconomicEvent.event_time >= window_start, EconomicEvent.event_time <= window_end)
        ).all()

        high_impact = [event for event in events if event.impact.upper() == "ALTO"]
        if high_impact:
            score -= 18
            reasons.append("Agenda economica carregada com evento de alto impacto.")
        else:
            score += 10
            reasons.append("Sem noticia forte proxima.")

        context = payload.context_news.lower()
        positive_terms = ("desinflacao", "liquidez", "corte de juros", "risk-on")
        negative_terms = ("guerra", "crise", "hawkish", "inflacao persistente", "fomc", "payroll")
        if any(term in context for term in positive_terms):
            score += 8
            reasons.append("Fluxo macro levemente favoravel ao ativo.")
        if any(term in context for term in negative_terms):
            score -= 10
            reasons.append("Sentimento macro pressiona a leitura atual.")

        return max(0.0, min(round(score, 2), 100.0)), reasons

    def _historical_score(self, payload: SnapshotInput, snapshot: dict[str, float | str | bool]) -> tuple[float, list[str]]:
        score = 52.0
        reasons: list[str] = []
        similar = self.db.scalars(
            select(MarketSnapshot).where(
                MarketSnapshot.symbol == payload.symbol,
                MarketSnapshot.timeframe == payload.timeframe,
                MarketSnapshot.trend == payload.trend,
            )
        ).all()

        if not similar:
            reasons.append("Base historica inicial ainda curta para esse contexto.")
            return score, reasons

        successful = [item for item in similar if item.future_result.upper() in {"WIN", "TARGET", "POSITIVE"}]
        success_rate = len(successful) / len(similar)
        score += success_rate * 30
        reasons.append(f"Historico semelhante indica taxa positiva de {round(success_rate * 100, 1)}%.")

        current_hour = payload.timestamp.hour
        same_hour = [item for item in similar if item.created_at.hour == current_hour]
        if same_hour:
            score += 6
            reasons.append("Horario atual possui amostra comparavel registrada.")

        score += 4 if float(snapshot["volatility_pct"]) <= 2.4 else -4
        return max(0.0, min(round(score, 2), 100.0)), reasons

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
            select(EconomicEvent).where(EconomicEvent.event_time >= datetime.now(UTC) - timedelta(hours=1))
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

    @staticmethod
    def _decision_from_score(score: float, trend: str) -> str:
        if score <= 50:
            return "NAO_OPERAR"
        if trend.lower() in {"alta", "bullish"}:
            return "COMPRA"
        if trend.lower() in {"baixa", "bearish"}:
            return "VENDA"
        return "NAO_OPERAR"

    @staticmethod
    def _risk_level(score: float, volatility: float, spread: float) -> str:
        if score >= 76 and volatility <= 2.4 and spread <= 1.2:
            return "Baixo"
        if score >= 60 and volatility <= 3.0 and spread <= 2.0:
            return "Moderado"
        return "Alto"


def summarize_reasons(records: Sequence[MarketSnapshot]) -> list[str]:
    if not records:
        return ["Sem leitura suficiente para gerar explicacoes."]
    top = sorted(records, key=lambda item: item.final_score, reverse=True)[0]
    return [part.strip() for part in top.reasoning.split("|") if part.strip()][:4]


def seed_demo_dataset(db: Session) -> None:
    base_time = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
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
