from __future__ import annotations

from datetime import datetime, timedelta, timezone

from market_intelligence.collectors import BinanceCollector, BlsCollector, FredCollector, MacroCalendarCollector, OandaCollector
from market_intelligence.config import MarketIntelligenceConfig
from market_intelligence.explanation import build_reasons
from market_intelligence.features import compute_macro_snapshot, compute_session_quality, compute_spread_score, compute_trend_snapshot, compute_volatility_score
from market_intelligence.models import CollectorIssue, DecisionResult, FeatureSnapshot
from market_intelligence.risk_blocks import build_blocks
from market_intelligence.storage import MarketIntelligenceStorage


class MarketIntelligenceEngine:
    def __init__(self, config: MarketIntelligenceConfig, storage: MarketIntelligenceStorage | None = None) -> None:
        self.config = config
        self.storage = storage or MarketIntelligenceStorage(config.storage_dir)
        self.oanda = OandaCollector(config)
        self.binance = BinanceCollector(config)
        self.bls = BlsCollector(config)
        self.fred = FredCollector(config)
        self.calendar = MacroCalendarCollector(config)

    def analyze_market(self, asset: str, timeframe: str) -> DecisionResult:
        now = datetime.now(timezone.utc)
        candles, issues = self._collect_market_data(asset, timeframe)
        if len(candles) < 20:
            issues.append(CollectorIssue(source="market-data", message="Dados insuficientes para analise robusta.", critical=True))

        fred_value, fred_issues = self.fred.fetch_latest(self.config.fred_dxy_series_id)
        bls_values, bls_issues = self.bls.fetch_latest([self.config.bls_cpi_series_id, self.config.bls_payroll_series_id])
        events, event_issues = self.calendar.fetch_upcoming_events(now)
        issues.extend(fred_issues)
        issues.extend(bls_issues)
        issues.extend(event_issues)

        dollar_strength = _normalize_dollar_strength(fred_value, bls_values)
        volatility_score = compute_volatility_score(candles)
        trend_direction, trend_strength = compute_trend_snapshot(candles)
        spread_score = compute_spread_score(candles)
        session_quality = compute_session_quality(now)
        macro_score, regime_hint, macro_reasons = compute_macro_snapshot(self.config, now, events, dollar_strength)

        regime = regime_hint
        if trend_direction == "LATERAL" and volatility_score < 45:
            regime = "LATERAL"
        elif volatility_score >= 80:
            regime = "ALTA_VOLATILIDADE"
        elif trend_strength >= 55:
            regime = "TENDENCIA"

        feature_snapshot = FeatureSnapshot(
            volatility_score=volatility_score,
            trend_direction=trend_direction,
            trend_strength=trend_strength,
            spread_score=spread_score,
            macro_score=macro_score,
            session_quality_score=session_quality,
            dollar_strength_score=dollar_strength,
            regime=regime,
            reasons=macro_reasons,
            data_sources=sorted({item.source for item in candles} | {event.source for event in events}),
        )

        technical_score = max(0.0, min(100.0, (trend_strength * 0.55) + ((100 - volatility_score) * 0.25) + ((100 - spread_score) * 0.20)))
        risk_score = max(0.0, min(100.0, (volatility_score * 0.35) + (spread_score * 0.30) + ((100 - session_quality) * 0.20) + (100 - macro_score) * 0.15))
        confidence_score = max(0.0, min(100.0, (technical_score * 0.55) + (macro_score * 0.25) + ((100 - risk_score) * 0.20)))

        blocks = build_blocks(self.config, feature_snapshot, issues, confidence_score)
        action = _decide_action(self.config.min_confidence_score, trend_direction, confidence_score, blocks)
        reasons = build_reasons(feature_snapshot, action)
        reasons.extend(issue.message for issue in issues if not issue.critical)

        result = DecisionResult(
            asset=asset,
            timeframe=timeframe,
            action=action,
            confidence_score=round(confidence_score, 2),
            technical_score=round(technical_score, 2),
            macro_score=round(macro_score, 2),
            risk_score=round(risk_score, 2),
            valid_until=now + _validity_delta(timeframe),
            reasons=reasons,
            blocks=blocks + [issue.message for issue in issues if issue.critical],
            created_at=now,
            regime=regime,
            data_sources=sorted(set(feature_snapshot.data_sources + [issue.source for issue in issues if issue.source])),
        )
        self.storage.save_decision(result)
        if events:
            self.storage.save_events(events)
        return result

    def _collect_market_data(self, asset: str, timeframe: str) -> tuple[list, list[CollectorIssue]]:
        if _is_crypto_asset(asset):
            return self.binance.fetch_candles(asset, timeframe)
        return self.oanda.fetch_candles(asset, timeframe)


def _is_crypto_asset(asset: str) -> bool:
    normalized = asset.upper()
    return any(token in normalized for token in ("USDT", "BTC", "ETH", "BNB", "XRP", "SOL", "ADA"))


def _normalize_dollar_strength(fred_value: float | None, bls_values: dict[str, float]) -> float:
    if fred_value is None:
        return 50.0
    payroll = bls_values.get("CES0000000001")
    payroll_boost = 5.0 if payroll and payroll > 150000 else -5.0 if payroll and payroll < 50000 else 0.0
    return max(0.0, min(100.0, (fred_value / 2.0) + payroll_boost))


def _decide_action(min_confidence_score: float, trend_direction: str, confidence_score: float, blocks: list[str]) -> str:
    if blocks:
        return "NAO_OPERAR"
    if confidence_score < min_confidence_score:
        return "NAO_OPERAR"
    if trend_direction == "ALTA":
        return "COMPRA"
    if trend_direction == "BAIXA":
        return "VENDA"
    return "NAO_OPERAR"


def _validity_delta(timeframe: str) -> timedelta:
    mapping = {
        "M1": timedelta(minutes=2),
        "M5": timedelta(minutes=7),
        "M15": timedelta(minutes=20),
        "H1": timedelta(minutes=75),
        "1m": timedelta(minutes=2),
        "5m": timedelta(minutes=7),
        "15m": timedelta(minutes=20),
        "1h": timedelta(minutes=75),
    }
    return mapping.get(timeframe.upper(), timedelta(minutes=5))
