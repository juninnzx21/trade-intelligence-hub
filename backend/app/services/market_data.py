from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from random import Random
from statistics import mean, pstdev

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import MarketSnapshot


@dataclass
class Candle:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


TIMEFRAME_TO_MINUTES = {
    "1m": 1,
    "5m": 5,
    "15m": 15,
    "1h": 60,
}

BINANCE_INTERVAL_MAP = {
    "1m": "1m",
    "5m": "5m",
    "15m": "15m",
    "1h": "1h",
}


class MarketDataService:
    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()

    def get_series(self, symbol: str, market: str, timeframe: str, limit: int = 120) -> tuple[list[Candle], str]:
        if market.upper() == "FOREX":
            live = self._fetch_oanda_series(symbol, timeframe, limit)
            if live:
                return live, "OANDA v20 Demo"
        if market.upper() == "CRYPTO":
            live = self._fetch_binance_series(symbol, timeframe, limit)
            if live:
                return live, "Binance Public API"
        return self._generate_demo_series(symbol, market, timeframe, limit), "Observer Demo Feed"

    def get_current_spread(self, symbol: str, market: str) -> float:
        if market.upper() == "CRYPTO":
            binance_symbol = symbol.replace("/", "")
            try:
                response = httpx.get(
                    "https://api.binance.com/api/v3/ticker/bookTicker",
                    params={"symbol": binance_symbol},
                    timeout=4.0,
                )
                response.raise_for_status()
                payload = response.json()
                ask = float(payload["askPrice"])
                bid = float(payload["bidPrice"])
                return round(max(ask - bid, 0.0), 6)
            except Exception:
                return 1.2
        latest = self.db.scalars(
            select(MarketSnapshot).where(MarketSnapshot.symbol == symbol).order_by(MarketSnapshot.created_at.desc())
        ).first()
        return latest.spread if latest else 1.0

    def _fetch_oanda_series(self, symbol: str, timeframe: str, limit: int) -> list[Candle]:
        if not self.settings.oanda_api_key:
            return []
        granularity_map = {
            "1m": "M1",
            "5m": "M5",
            "15m": "M15",
            "1h": "H1",
        }
        granularity = granularity_map.get(timeframe)
        if not granularity:
            return []
        instrument = symbol.replace("/", "_")
        try:
            response = httpx.get(
                f"{self.settings.oanda_base_url}/v3/instruments/{instrument}/candles",
                params={"price": "MBA", "granularity": granularity, "count": limit},
                headers={"Authorization": f"Bearer {self.settings.oanda_api_key}"},
                timeout=6.0,
            )
            response.raise_for_status()
            payload = response.json()
            candles: list[Candle] = []
            for item in payload.get("candles", []):
                if not item.get("complete", False):
                    continue
                mid = item.get("mid") or {}
                candles.append(
                    Candle(
                        timestamp=datetime.fromisoformat(item["time"].replace("Z", "+00:00")).astimezone(UTC),
                        open=float(mid.get("o", 0.0)),
                        high=float(mid.get("h", 0.0)),
                        low=float(mid.get("l", 0.0)),
                        close=float(mid.get("c", 0.0)),
                        volume=float(item.get("volume", 0.0)),
                    )
                )
            return candles
        except Exception:
            return []

    def _fetch_binance_series(self, symbol: str, timeframe: str, limit: int) -> list[Candle]:
        interval = BINANCE_INTERVAL_MAP.get(timeframe)
        if not interval:
            return []
        try:
            response = httpx.get(
                "https://api.binance.com/api/v3/klines",
                params={"symbol": symbol.replace("/", ""), "interval": interval, "limit": limit},
                timeout=5.0,
            )
            response.raise_for_status()
            rows = response.json()
            candles = [
                Candle(
                    timestamp=datetime.fromtimestamp(item[0] / 1000, tz=UTC),
                    open=float(item[1]),
                    high=float(item[2]),
                    low=float(item[3]),
                    close=float(item[4]),
                    volume=float(item[5]),
                )
                for item in rows
            ]
            return candles
        except Exception:
            return []

    def _generate_demo_series(self, symbol: str, market: str, timeframe: str, limit: int) -> list[Candle]:
        latest = self.db.scalars(
            select(MarketSnapshot).where(MarketSnapshot.symbol == symbol).order_by(MarketSnapshot.created_at.desc())
        ).first()
        if latest:
            base_price = latest.close
            base_volume = max(latest.volume, 5000.0)
        else:
            defaults = {
                "EUR/USD": 1.0835,
                "GBP/USD": 1.2652,
                "BTC/USDT": 68200.0,
                "ETH/USDT": 3310.0,
            }
            base_price = defaults.get(symbol, 100.0)
            base_volume = 8000.0

        seed = sum(ord(char) for char in f"{symbol}-{market}-{timeframe}")
        rng = Random(seed)
        step_minutes = TIMEFRAME_TO_MINUTES.get(timeframe, 5)
        start = datetime.now(UTC) - timedelta(minutes=step_minutes * limit)
        candles: list[Candle] = []
        previous_close = base_price * (0.98 + rng.random() * 0.04)

        for index in range(limit):
            drift = (rng.random() - 0.48) * (0.0025 if market.upper() == "FOREX" else 0.009)
            noise = (rng.random() - 0.5) * (0.0018 if market.upper() == "FOREX" else 0.006)
            open_price = previous_close
            close_price = max(0.0001, open_price * (1 + drift + noise))
            high_price = max(open_price, close_price) * (1 + rng.random() * 0.0018)
            low_price = min(open_price, close_price) * (1 - rng.random() * 0.0016)
            volume = base_volume * (0.72 + rng.random() * 0.8)
            candles.append(
                Candle(
                    timestamp=start + timedelta(minutes=step_minutes * index),
                    open=open_price,
                    high=high_price,
                    low=low_price,
                    close=close_price,
                    volume=volume,
                )
            )
            previous_close = close_price

        return candles


def _ema(values: list[float], period: int) -> list[float]:
    multiplier = 2 / (period + 1)
    ema_values = [values[0]]
    for value in values[1:]:
        ema_values.append((value - ema_values[-1]) * multiplier + ema_values[-1])
    return ema_values


def calculate_indicator_snapshot(candles: list[Candle], spread: float) -> dict[str, float | str | bool]:
    closes = [item.close for item in candles]
    highs = [item.high for item in candles]
    lows = [item.low for item in candles]
    volumes = [item.volume for item in candles]
    latest = candles[-1]
    prev = candles[-2] if len(candles) > 1 else latest

    sma_fast = mean(closes[-9:])
    sma_slow = mean(closes[-21:])
    ema12 = _ema(closes[-40:], 12)
    ema26 = _ema(closes[-40:], 26)
    macd_line = ema12[-1] - ema26[-1]
    macd_signal = _ema([a - b for a, b in zip(ema12, ema26)], 9)[-1]
    deltas = [closes[idx] - closes[idx - 1] for idx in range(1, len(closes))]
    gains = [max(delta, 0) for delta in deltas[-14:]]
    losses = [abs(min(delta, 0)) for delta in deltas[-14:]]
    avg_gain = mean(gains) if gains else 0.0
    avg_loss = mean(losses) if losses else 0.0001
    rs = avg_gain / avg_loss if avg_loss else 0.0
    rsi = 100 - (100 / (1 + rs)) if avg_loss else 100.0
    band_basis = mean(closes[-20:])
    band_dev = pstdev(closes[-20:]) if len(closes) >= 20 else 0.0
    bollinger_upper = band_basis + (2 * band_dev)
    bollinger_lower = band_basis - (2 * band_dev)
    true_ranges = [
        max(
            highs[idx] - lows[idx],
            abs(highs[idx] - closes[idx - 1]),
            abs(lows[idx] - closes[idx - 1]),
        )
        for idx in range(1, len(closes))
    ]
    atr = mean(true_ranges[-14:]) if true_ranges else 0.0
    cumulative_volume = sum(volumes[-30:]) or 1.0
    vwap = sum(c.close * c.volume for c in candles[-30:]) / cumulative_volume
    support = min(lows[-20:])
    resistance = max(highs[-20:])
    volatility_pct = (atr / latest.close) * 100 if latest.close else 0.0
    momentum_pct = ((latest.close / closes[-6]) - 1) * 100 if len(closes) > 6 and closes[-6] else 0.0
    candle_range = max(latest.high - latest.low, 0.000001)
    candle_strength = abs(latest.close - latest.open) / candle_range
    primary_trend = "alta" if sma_fast > sma_slow and latest.close > vwap else "baixa" if sma_fast < sma_slow and latest.close < vwap else "lateral"
    secondary_trend = "alta" if latest.close > prev.close else "baixa" if latest.close < prev.close else "lateral"
    breakout = latest.close > resistance * 0.998 or latest.close < support * 1.002
    pullback = (primary_trend == "alta" and latest.close < sma_fast and latest.close > sma_slow) or (
        primary_trend == "baixa" and latest.close > sma_fast and latest.close < sma_slow
    )
    lateral = abs(sma_fast - sma_slow) / latest.close < 0.0012 if latest.close else True
    pattern = "engolfo_de_alta" if latest.close > latest.open and prev.close < prev.open and latest.close > prev.open else (
        "engolfo_de_baixa" if latest.close < latest.open and prev.close > prev.open and latest.close < prev.open else "neutro"
    )

    return {
        "trend_primary": primary_trend,
        "trend_secondary": secondary_trend,
        "sma_fast": round(sma_fast, 6),
        "sma_slow": round(sma_slow, 6),
        "rsi": round(rsi, 2),
        "macd": round(macd_line, 6),
        "macd_signal": round(macd_signal, 6),
        "bollinger_upper": round(bollinger_upper, 6),
        "bollinger_lower": round(bollinger_lower, 6),
        "atr": round(atr, 6),
        "vwap": round(vwap, 6),
        "support": round(support, 6),
        "resistance": round(resistance, 6),
        "breakout": breakout,
        "pullback": pullback,
        "lateral": lateral,
        "candle_strength": round(candle_strength, 2),
        "pattern": pattern,
        "momentum_pct": round(momentum_pct, 2),
        "volatility_pct": round(volatility_pct, 2),
        "spread": round(spread, 6),
    }
