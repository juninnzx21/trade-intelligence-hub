from __future__ import annotations

import json
import logging
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import load_settings
from pin_guard import PinGuard


def build_settings(tmp_path: Path):
    env = tmp_path / ".env"
    env.write_text(
        "\n".join(
            [
                "ASSISTANT_PIN=12345690",
                "PIN_HASH_FILE=storage/pin.hash",
                "PIN_MAX_ATTEMPTS=3",
                "ENABLE_LOCAL_ENCRYPTION=true",
                "ASSISTANT_MASTER_KEY=test-master-key",
            ]
        ),
        encoding="utf-8",
    )
    return load_settings(tmp_path)


def test_creates_hash_file_without_plain_pin(tmp_path: Path) -> None:
    settings = build_settings(tmp_path)
    guard = PinGuard(settings, logging.getLogger("pin_test"))
    guard.ensure_pin_hash()
    payload = json.loads(settings.pin_hash_file.read_text(encoding="utf-8"))
    serialized = json.dumps(payload)
    assert settings.pin_hash_file.exists()
    assert "12345690" not in serialized


def test_validates_correct_pin(tmp_path: Path) -> None:
    settings = build_settings(tmp_path)
    guard = PinGuard(settings, logging.getLogger("pin_test"))
    guard.ensure_pin_hash()
    assert guard.validate_pin("12345690")
    assert guard.is_validated()


def test_rejects_wrong_pin(tmp_path: Path) -> None:
    settings = build_settings(tmp_path)
    guard = PinGuard(settings, logging.getLogger("pin_test"))
    guard.ensure_pin_hash()
    assert not guard.validate_pin("00000000")
    assert not guard.is_validated()


def test_blocks_after_three_wrong_attempts(tmp_path: Path) -> None:
    settings = build_settings(tmp_path)
    guard = PinGuard(settings, logging.getLogger("pin_test"))
    guard.ensure_pin_hash()
    assert not guard.validate_pin("00000000")
    assert not guard.validate_pin("11111111")
    assert not guard.validate_pin("22222222")
    assert guard.status().blocked
    assert guard.remaining_attempts() == 0
