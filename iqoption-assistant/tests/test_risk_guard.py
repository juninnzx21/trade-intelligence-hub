from __future__ import annotations

from datetime import datetime
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import Settings
from risk_guard import ArmSessionContext, ExecutionContext, can_arm_session, can_auto_click, ensure_real_account_protection, infer_account_mode, is_demo_account, pre_click_guard
from signal_parser import BRAZIL_TZ, build_signal


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


def test_detect_demo_account() -> None:
    assert is_demo_account("Conta DEMO")
    assert is_demo_account("Practice balance")
    assert not is_demo_account("Conta Real")


def test_infer_account_mode_variations() -> None:
    assert infer_account_mode("Conta demo", "Saldo demo") == "DEMO"
    assert infer_account_mode("Practice balance") == "DEMO"
    assert infer_account_mode("Conta Real") == "REAL"
    assert infer_account_mode("Balance available") == "DESCONHECIDO"


def test_block_auto_click_when_dry_run_true() -> None:
    decision = can_auto_click(
        settings=make_settings(dry_run=True, allow_auto_click=True),
        allow_click_demo_only_flag=True,
        account_is_demo=True,
        confirmation_text="CONFIRMO DEMO",
    )
    assert not decision.allowed
    assert "DRY_RUN=true" in decision.reason


def test_block_real_account_when_demo_only() -> None:
    decision = ensure_real_account_protection(account_is_demo=False, demo_only=True)
    assert not decision.allowed
    assert "conta real" in decision.reason.lower() or "nao identificada" in decision.reason.lower()


def test_allow_demo_click_only_with_all_guards() -> None:
    decision = can_auto_click(
        settings=make_settings(dry_run=False, demo_only=True, allow_auto_click=True),
        allow_click_demo_only_flag=True,
        account_is_demo=True,
        confirmation_text="CONFIRMO DEMO",
    )
    assert decision.allowed


def test_pre_click_guard_blocks_when_dry_run() -> None:
    signal = build_signal("EUR/USD", "COMPRA", "14:35", "M1", now=datetime(2026, 5, 2, 14, 0, tzinfo=BRAZIL_TZ))
    context = ExecutionContext(
        session_armed=True,
        account_is_demo=True,
        active_asset_matches=True,
        stop_flag_exists=False,
        trades_executed=0,
        operation_in_progress=False,
        browser_alive=True,
    )
    decision = pre_click_guard(make_settings(dry_run=True, allow_auto_click=True), signal, context, now=signal.entry_at)
    assert not decision.allowed
    assert "DRY_RUN=true" in decision.reason


def test_auto_click_guard_requires_demo_only_true() -> None:
    decision = can_auto_click(
        settings=make_settings(dry_run=False, demo_only=False, allow_auto_click=True),
        allow_click_demo_only_flag=True,
        account_is_demo=True,
        confirmation_text="CONFIRMO DEMO",
    )
    assert not decision.allowed
    assert "DEMO_ONLY=false" in decision.reason


def test_arm_session_requires_valid_pin_and_integrity() -> None:
    context = ArmSessionContext(
        pin_validated=False,
        pin_blocked=False,
        integrity_ok=True,
        stop_flag_exists=False,
        account_mode="DEMO",
    )
    decision = can_arm_session(make_settings(dry_run=False, allow_auto_click=True), context)
    assert not decision.allowed
    assert "PIN nao validado" in decision.reason


def test_arm_session_allows_demo_when_guards_pass() -> None:
    context = ArmSessionContext(
        pin_validated=True,
        pin_blocked=False,
        integrity_ok=True,
        stop_flag_exists=False,
        account_mode="DEMO",
    )
    decision = can_arm_session(make_settings(dry_run=False, allow_auto_click=True), context)
    assert decision.allowed


def test_arm_session_blocks_real_account_explicitly() -> None:
    context = ArmSessionContext(
        pin_validated=True,
        pin_blocked=False,
        integrity_ok=True,
        stop_flag_exists=False,
        account_mode="REAL",
    )
    decision = can_arm_session(make_settings(dry_run=False, allow_auto_click=True), context)
    assert not decision.allowed
    assert "conta REAL detectada" in decision.reason
