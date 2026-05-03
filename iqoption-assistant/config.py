from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:
    def load_dotenv(dotenv_path: Path | str | None = None, *_args: object, **_kwargs: object) -> bool:
        if dotenv_path is None:
            return False
        path = Path(dotenv_path)
        if not path.exists():
            return False
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())
        return True


def _to_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


@dataclass(frozen=True)
class Settings:
    root_dir: Path
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
    enable_local_encryption: bool
    assistant_pin: str | None
    assistant_master_key: str | None
    logs_dir: Path
    storage_dir: Path
    stop_file: Path
    encrypted_audit_file: Path
    integrity_manifest: Path
    pin_hash_file: Path
    pin_max_attempts: int


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
    encrypted_audit_raw = os.getenv("ENCRYPTED_AUDIT_FILE", "storage/logs/audit.secure.log")
    encrypted_audit_file = root / encrypted_audit_raw
    encrypted_audit_file.parent.mkdir(parents=True, exist_ok=True)
    integrity_manifest_raw = os.getenv("INTEGRITY_MANIFEST", "storage/integrity_manifest.json")
    integrity_manifest = root / integrity_manifest_raw
    integrity_manifest.parent.mkdir(parents=True, exist_ok=True)
    pin_hash_file_raw = os.getenv("PIN_HASH_FILE", "storage/pin.hash")
    pin_hash_file = root / pin_hash_file_raw
    pin_hash_file.parent.mkdir(parents=True, exist_ok=True)

    return Settings(
        root_dir=root,
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
        enable_local_encryption=_to_bool(os.getenv("ENABLE_LOCAL_ENCRYPTION"), True),
        assistant_pin=os.getenv("ASSISTANT_PIN") or None,
        assistant_master_key=os.getenv("ASSISTANT_MASTER_KEY") or None,
        logs_dir=storage_logs_dir,
        storage_dir=storage_dir,
        stop_file=stop_file,
        encrypted_audit_file=encrypted_audit_file,
        integrity_manifest=integrity_manifest,
        pin_hash_file=pin_hash_file,
        pin_max_attempts=int(os.getenv("PIN_MAX_ATTEMPTS", "3")),
    )
