from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class ScoreBreakdown:
    score: float
    reasons: list[str]


@dataclass
class TimingPlan:
    entry_time: datetime | None
    exit_time: datetime | None
    duration_minutes: int | None
    duration_label: str | None
    duration_reason: str | None
    signal_valid_until: datetime | None


@dataclass
class ValidationResult:
    blockers: list[str]
    warnings: list[str]
