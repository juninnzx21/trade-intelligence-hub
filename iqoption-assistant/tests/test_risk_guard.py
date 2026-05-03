from __future__ import annotations

from datetime import datetime
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import Settings
from risk_guard import ExecutionContext, can_auto_click, ensure_real_account_protection, is_demo_account, pre_click_guard
from signal_parser import BRAZIL_TZ, build_signal


def make_settings(**overrides: object) -> Settings:
    base = dict(
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
        logs_dir=Path("storage/logs"),
        storage_dir=Path("storage"),
        stop_file=Path("storage/STOP_TRADING.flag"),
    )
    base.update(overrides)
    return Settings(**base)


def test_detect_demo_account() -> None:
    assert is_demo_account("Conta DEMO")
    assert is_demo_account("Practice balance")
    assert not is_demo_account("Conta Real")


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
