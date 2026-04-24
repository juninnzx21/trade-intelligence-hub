from __future__ import annotations

from app.schemas.analysis import SnapshotInput
from app.services.engines.common import ScoreBreakdown


def calculate_technical_score(payload: SnapshotInput, snapshot: dict[str, float | str | bool]) -> ScoreBreakdown:
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
        reasons.append("Estrutura lateral reduz confianca operacional.")

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

    return ScoreBreakdown(score=max(0.0, min(round(score, 2), 100.0)), reasons=reasons)
