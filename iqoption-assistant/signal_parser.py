from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import re
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


try:
    BRAZIL_TZ = ZoneInfo("America/Sao_Paulo")
except ZoneInfoNotFoundError:
    BRAZIL_TZ = timezone(timedelta(hours=-3), name="America/Sao_Paulo")
SUPPORTED_EXPIRATIONS = {"M1": 1, "M5": 5, "M15": 15, "H1": 60}
SUPPORTED_DIRECTIONS = {"COMPRA", "VENDA"}
ASSET_PATTERN = re.compile(r"^[A-Z0-9]{3,10}/[A-Z0-9]{3,10}$")


@dataclass(frozen=True)
class TradeSignal:
    asset: str
    direction: str
    entry_time_text: str
    expiration: str
    entry_at: datetime

    @property
    def expiration_minutes(self) -> int:
        return SUPPORTED_EXPIRATIONS[self.expiration]


def normalize_asset(asset: str) -> str:
    return asset.strip().upper().replace("-", "/")


def validate_asset(asset: str) -> str:
    normalized = normalize_asset(asset)
    if not ASSET_PATTERN.match(normalized):
        raise ValueError("Ativo invalido. Use formato como EUR/USD ou BTC/USDT.")
    return normalized


def validate_direction(direction: str) -> str:
    normalized = direction.strip().upper()
    if normalized not in SUPPORTED_DIRECTIONS:
        raise ValueError("Direcao invalida. Use COMPRA ou VENDA.")
    return normalized


def validate_expiration(expiration: str) -> str:
    normalized = expiration.strip().upper()
    if normalized not in SUPPORTED_EXPIRATIONS:
        raise ValueError("Expiracao invalida. Use M1, M5, M15 ou H1.")
    return normalized


def build_entry_datetime(entry_time_text: str, now: datetime | None = None) -> datetime:
    current = now.astimezone(BRAZIL_TZ) if now else datetime.now(BRAZIL_TZ)
    if not re.match(r"^\d{2}:\d{2}$", entry_time_text.strip()):
        raise ValueError("Horario invalido. Use HH:MM.")

    hour, minute = [int(part) for part in entry_time_text.split(":")]
    if hour > 23 or minute > 59:
        raise ValueError("Horario invalido. Use HH:MM entre 00:00 e 23:59.")

    target = current.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if target <= current:
        target = target + timedelta(days=1)
    return target


def parse_signal_text(text: str, now: datetime | None = None) -> TradeSignal:
    fields: dict[str, str] = {}
    raw_text = text.replace("|", "\n")
    for raw_line in raw_text.splitlines():
        line = raw_line.strip()
        if not line or "=" not in line:
            continue
        key, value = line.split("=", 1)
        fields[key.strip().lower()] = value.strip()

    return build_signal(
        asset=fields.get("ativo", ""),
        direction=fields.get("direcao", ""),
        entry_time_text=fields.get("horario", ""),
        expiration=fields.get("expiracao", ""),
        now=now,
    )


def build_signal(asset: str, direction: str, entry_time_text: str, expiration: str, now: datetime | None = None) -> TradeSignal:
    normalized_asset = validate_asset(asset)
    normalized_direction = validate_direction(direction)
    normalized_expiration = validate_expiration(expiration)
    entry_at = build_entry_datetime(entry_time_text.strip(), now=now)
    return TradeSignal(
        asset=normalized_asset,
        direction=normalized_direction,
        entry_time_text=entry_time_text.strip(),
        expiration=normalized_expiration,
        entry_at=entry_at,
    )


def parse_signal_input(
    raw_text: str | None = None,
    *,
    asset: str | None = None,
    direction: str | None = None,
    entry_time_text: str | None = None,
    expiration: str | None = None,
    now: datetime | None = None,
) -> TradeSignal:
    if raw_text and raw_text.strip():
        return parse_signal_text(raw_text, now=now)
    return build_signal(
        asset=asset or "",
        direction=direction or "",
        entry_time_text=entry_time_text or "",
        expiration=expiration or "",
        now=now,
    )
