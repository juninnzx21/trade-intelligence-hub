from __future__ import annotations

from app.services.engines.common import ValidationResult


def adjust_for_validation(score: float, validation: ValidationResult) -> float:
    if validation.blockers:
        return min(score, 50.0)
    return score
