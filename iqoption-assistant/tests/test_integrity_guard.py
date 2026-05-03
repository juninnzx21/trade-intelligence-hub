from __future__ import annotations

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import load_settings
from integrity_guard import IntegrityGuard, MONITORED_FILES


def build_workspace(tmp_path: Path) -> Path:
    for name in MONITORED_FILES:
        (tmp_path / name).write_text(f"# {name}\n", encoding="utf-8")
    (tmp_path / ".env").write_text(
        "\n".join(
            [
                "INTEGRITY_MANIFEST=storage/integrity_manifest.json",
                "PIN_HASH_FILE=storage/pin.hash",
                "ASSISTANT_PIN=12345690",
                "ASSISTANT_MASTER_KEY=test-master-key",
            ]
        ),
        encoding="utf-8",
    )
    return tmp_path


def test_writes_manifest(tmp_path: Path) -> None:
    workspace = build_workspace(tmp_path)
    settings = load_settings(workspace)
    guard = IntegrityGuard(settings)
    manifest_path = guard.write_manifest()
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest_path.exists()
    assert set(payload["files"]) == set(MONITORED_FILES)


def test_check_integrity_ok(tmp_path: Path) -> None:
    workspace = build_workspace(tmp_path)
    settings = load_settings(workspace)
    guard = IntegrityGuard(settings)
    guard.write_manifest()
    result = guard.check_integrity()
    assert result.ok
    assert result.status == "OK"


def test_detects_modified_file(tmp_path: Path) -> None:
    workspace = build_workspace(tmp_path)
    settings = load_settings(workspace)
    guard = IntegrityGuard(settings)
    guard.write_manifest()
    (workspace / "main.py").write_text("# modified\n", encoding="utf-8")
    result = guard.check_integrity()
    assert not result.ok
    assert result.status == "FALHA"
    assert any("main.py" in detail for detail in result.details)
