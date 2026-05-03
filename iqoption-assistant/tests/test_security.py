from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import Settings
from security import RedactingFilter, SecurityManager


def make_settings(**overrides: object) -> Settings:
    root = Path(".")
    base = dict(
        root_dir=root,
        dry_run=True,
        demo_only=True,
        allow_auto_click=False,
        session_arm_required=True,
        max_trades_per_session=5,
        max_daily_loss=0.0,
        iq_option_url="https://iqoption.com/traderoom",
        chrome_path=None,
        chrome_debug_port=9222,
        chrome_user_data_dir=Path(".chrome-profile"),
        login_wait_timeout_seconds=600,
        alert_before_seconds=10,
        log_level="INFO",
        enable_local_encryption=True,
        assistant_pin="12345690",
        assistant_master_key="super-secret-local-key",
        logs_dir=Path("storage/logs"),
        storage_dir=Path("storage"),
        stop_file=Path("storage/STOP_TRADING.flag"),
        encrypted_audit_file=Path("storage/logs/audit.secure.log"),
        integrity_manifest=Path("storage/integrity_manifest.json"),
        pin_hash_file=Path("storage/pin.hash"),
        pin_max_attempts=3,
    )
    base.update(overrides)
    return Settings(**base)


def test_security_manager_reports_encryption_ready() -> None:
    manager = SecurityManager(make_settings())
    assert manager.encryption_ready


def test_redacting_filter_masks_master_key() -> None:
    import logging

    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="ASSISTANT_MASTER_KEY=my-secret-value",
        args=(),
        exc_info=None,
    )
    result = RedactingFilter().filter(record)
    assert result
    assert "***" in record.msg
    assert "my-secret-value" not in record.msg
