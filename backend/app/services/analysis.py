from collections.abc import Sequence
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import EconomicEvent, MarketSnapshot
from app.schemas.analysis import AnalysisResponse, SnapshotInput


class AnalysisEngine:
    def __init__(self, db: Session):
        self.db = db

    def analyze(self, payload: SnapshotInput) -> AnalysisResponse:
        blockers = self._evaluate_blockers(payload)
        technical_score, technical_reasons = self._technical_score(payload)
        fundamental_score, fundamental_reasons = self._fundamental_score(payload)
        historical_score, historical_reasons = self._historical_score(payload)

        final_score = round((technical_score * 0.45) + (fundamental_score * 0.25) + (historical_score * 0.30), 2)
        reasons = technical_reasons + fundamental_reasons + historical_reasons

        if blockers:
            final_score = min(final_score, 50)
            decision = "NAO_OPERAR"
            risk_level = "Alto"
        else:
            decision = self._decision_from_score(final_score, payload.trend)
            risk_level = self._risk_level(final_score, payload.volatility, payload.spread)

        return AnalysisResponse(
            symbol=payload.symbol,
            decision=decision,
            score=final_score,
            technical_score=technical_score,
            fundamental_score=fundamental_score,
            historical_score=historical_score,
            risk_level=risk_level,
            blockers=blockers,
            reasons=reasons[:6],
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
            reasoning=" | ".join(analysis.reasons + analysis.blockers),
        )
        self.db.add(snapshot)
        self.db.commit()
        self.db.refresh(snapshot)
        return snapshot

    def _evaluate_blockers(self, payload: SnapshotInput) -> list[str]:
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
        return blockers

    def _technical_score(self, payload: SnapshotInput) -> tuple[float, list[str]]:
        score = 50.0
        reasons: list[str] = []
        body = payload.close - payload.open
        amplitude = max(payload.high - payload.low, 0.0001)

        if payload.trend.lower() in {"alta", "bullish"}:
            score += 14
            reasons.append("Tendencia primaria de alta confirmada.")
        elif payload.trend.lower() in {"baixa", "bearish"}:
            score += 14
            reasons.append("Tendencia primaria de baixa confirmada.")
        else:
            score -= 8
            reasons.append("Estrutura tecnica sem direcao limpa.")

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
            reasons.append("Sem evento macro critico no curto prazo.")

        context = payload.context_news.lower()
        positive_terms = ("desinflacao", "liquidez", "corte de juros", "risk-on")
        negative_terms = ("guerra", "crise", "hawkish", "inflacao persistente")
        if any(term in context for term in positive_terms):
            score += 8
            reasons.append("Fluxo macro levemente favoravel ao ativo.")
        if any(term in context for term in negative_terms):
            score -= 10
            reasons.append("Sentimento macro pressiona a leitura atual.")

        return max(0.0, min(round(score, 2), 100.0)), reasons

    def _historical_score(self, payload: SnapshotInput) -> tuple[float, list[str]]:
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

        successful = [
            item for item in similar
            if item.future_result.upper() in {"WIN", "TARGET", "POSITIVE"}
        ]
        success_rate = len(successful) / len(similar)
        score += success_rate * 30
        reasons.append(
            f"Historico semelhante indica taxa positiva de {round(success_rate * 100, 1)}%."
        )

        current_hour = payload.timestamp.hour
        same_hour = [item for item in similar if item.created_at.hour == current_hour]
        if same_hour:
            score += 6
            reasons.append("Horario atual possui amostra comparavel registrada.")

        return max(0.0, min(round(score, 2), 100.0)), reasons

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
    if db.scalars(select(MarketSnapshot)).first():
        return

    base_time = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    samples = [
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
    ]

    events = [
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
    ]

    for sample in samples:
        db.add(MarketSnapshot(**sample))
    for event in events:
        db.add(event)
    db.commit()
