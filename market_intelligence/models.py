from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class MarketCandle:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    spread: float
    source: str


@dataclass(frozen=True)
class MacroEvent:
    event_time: datetime
    title: str
    impact: str
    source: str
    region: str
    related_assets: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class CollectorIssue:
    source: str
    message: str
    critical: bool


@dataclass(frozen=True)
class FeatureSnapshot:
    volatility_score: float
    trend_direction: str
    trend_strength: float
    spread_score: float
    macro_score: float
    session_quality_score: float
    dollar_strength_score: float
    regime: str
    reasons: list[str] = field(default_factory=list)
    data_sources: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class DecisionResult:
    asset: str
    timeframe: str
    action: str
    confidence_score: float
    technical_score: float
    macro_score: float
    risk_score: float
    valid_until: datetime
    reasons: list[str]
    blocks: list[str]
    created_at: datetime
    regime: str
    data_sources: list[str]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["valid_until"] = self.valid_until.isoformat()
        payload["created_at"] = self.created_at.isoformat()
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "DecisionResult":
        return cls(
            asset=payload["asset"],
            timeframe=payload["timeframe"],
            action=payload["action"],
            confidence_score=float(payload["confidence_score"]),
            technical_score=float(payload["technical_score"]),
            macro_score=float(payload["macro_score"]),
            risk_score=float(payload["risk_score"]),
            valid_until=datetime.fromisoformat(payload["valid_until"]),
            reasons=list(payload.get("reasons", [])),
            blocks=list(payload.get("blocks", [])),
            created_at=datetime.fromisoformat(payload["created_at"]),
            regime=payload.get("regime", "DESCONHECIDO"),
            data_sources=list(payload.get("data_sources", [])),
        )
