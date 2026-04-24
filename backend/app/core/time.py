from __future__ import annotations

from datetime import UTC, datetime
from zoneinfo import ZoneInfo


UTC_TZ = UTC
BRAZIL_TZ = ZoneInfo("America/Sao_Paulo")


def utc_now() -> datetime:
    return datetime.now(UTC_TZ)


def to_brazil(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC_TZ)
    return dt.astimezone(BRAZIL_TZ)


def to_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=BRAZIL_TZ)
    return dt.astimezone(UTC_TZ)
