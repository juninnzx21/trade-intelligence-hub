from __future__ import annotations

from datetime import datetime


def compute_session_quality(now: datetime) -> float:
    hour = now.hour
    if 8 <= hour <= 12:
        return 82.0
    if 13 <= hour <= 16:
        return 76.0
    if 17 <= hour <= 20:
        return 58.0
    if 21 <= hour <= 23:
        return 32.0
    return 28.0
