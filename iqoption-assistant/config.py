from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:
    def load_dotenv(*_args: object, **_kwargs: object) -> bool:
        return False


def _to_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


@dataclass(frozen=True)
class Settings:
    dry_run: bool
    demo_only: bool
    allow_auto_click: bool
    session_arm_required: bool
    max_trades_per_session: int
    max_daily_loss: float
    iq_option_url: str
    chrome_path: str | None
    chrome_debug_port: int
    chrome_user_data_dir: Path
    login_wait_timeout_seconds: int
    alert_before_seconds: int
    log_level: str
    logs_dir: Path
    storage_dir: Path
    stop_file: Path


def load_settings(base_dir: Path | None = None) -> Settings:
    root = base_dir or Path(__file__).resolve().parent
    env_path = root / ".env"
    if env_path.exists():
        load_dotenv(env_path)

    logs_dir = root / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    storage_dir = root / "storage"
    storage_dir.mkdir(parents=True, exist_ok=True)
    storage_logs_dir = storage_dir / "logs"
    storage_logs_dir.mkdir(parents=True, exist_ok=True)

    chrome_user_data_dir = root / os.getenv("CHROME_USER_DATA_DIR", ".chrome-profile")
    chrome_user_data_dir.mkdir(parents=True, exist_ok=True)

    stop_file_raw = os.getenv("STOP_FILE", "storage/STOP_TRADING.flag")
    stop_file = root / stop_file_raw
    stop_file.parent.mkdir(parents=True, exist_ok=True)

    return Settings(
        dry_run=_to_bool(os.getenv("DRY_RUN"), True),
        demo_only=_to_bool(os.getenv("DEMO_ONLY"), True),
        allow_auto_click=_to_bool(os.getenv("ALLOW_AUTO_CLICK"), False),
        session_arm_required=_to_bool(os.getenv("SESSION_ARM_REQUIRED"), True),
        max_trades_per_session=int(os.getenv("MAX_TRADES_PER_SESSION", "5")),
        max_daily_loss=float(os.getenv("MAX_DAILY_LOSS", "0")),
        iq_option_url=os.getenv("IQ_OPTION_URL", "https://iqoption.com/traderoom"),
        chrome_path=os.getenv("CHROME_PATH") or None,
        chrome_debug_port=int(os.getenv("CHROME_DEBUG_PORT", "9222")),
        chrome_user_data_dir=chrome_user_data_dir,
        login_wait_timeout_seconds=int(os.getenv("LOGIN_WAIT_TIMEOUT_SECONDS", "600")),
        alert_before_seconds=int(os.getenv("ALERT_BEFORE_SECONDS", "10")),
        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        logs_dir=storage_logs_dir,
        storage_dir=storage_dir,
        stop_file=stop_file,
    )
