from __future__ import annotations

from market_intelligence.config import MarketIntelligenceConfig
from market_intelligence.models import CollectorIssue, FeatureSnapshot


def build_blocks(
    config: MarketIntelligenceConfig,
    features: FeatureSnapshot,
    issues: list[CollectorIssue],
    confidence_score: float,
) -> list[str]:
    blocks: list[str] = []
    if any(issue.critical for issue in issues):
        blocks.append("Fonte critica indisponivel ou falhou.")
    if confidence_score < config.min_confidence_score:
        blocks.append(f"Score final abaixo do minimo configurado ({config.min_confidence_score}).")
    if features.volatility_score >= 80:
        blocks.append("Volatilidade anormal para o timeframe.")
    if features.spread_score >= 75:
        blocks.append("Spread/risco de liquidez elevado.")
    if features.session_quality_score <= 35:
        blocks.append("Horario historicamente ruim para esse contexto.")
    if features.regime == "NOTICIA_PROXIMA":
        blocks.append("Noticia macro de alto impacto muito proxima.")
    if features.regime == "LATERAL":
        blocks.append("Mercado lateral sem vantagem estatistica clara.")
    return blocks
