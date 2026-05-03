from __future__ import annotations

import logging
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

from audit_exporter import AuditExporter
from config import load_settings
from security import SecurityManager


def build_settings(tmp_path: Path, master_key: str = "test-master-key"):
    for key in ("ASSISTANT_PIN", "ASSISTANT_MASTER_KEY", "ENABLE_LOCAL_ENCRYPTION", "ENCRYPTED_AUDIT_FILE", "PIN_HASH_FILE", "INTEGRITY_MANIFEST"):
        os.environ.pop(key, None)
    (tmp_path / ".env").write_text(
        "\n".join(
            [
                "ASSISTANT_PIN=12345690",
                f"ASSISTANT_MASTER_KEY={master_key}",
                "ENABLE_LOCAL_ENCRYPTION=true",
                "ENCRYPTED_AUDIT_FILE=storage/logs/audit.secure.log",
                "PIN_HASH_FILE=storage/pin.hash",
                "INTEGRITY_MANIFEST=storage/integrity_manifest.json",
            ]
        ),
        encoding="utf-8",
    )
    return load_settings(tmp_path)


def test_exports_masked_audit_log(tmp_path: Path) -> None:
    settings = build_settings(tmp_path)
    security = SecurityManager(settings)
    security.audit_event(
        "test",
        {
            "line": "ASSISTANT_PIN=12345690 ASSISTANT_MASTER_KEY=secret authorization: Bearer123 cookie: abc token=zzz password=top",
        },
    )
    exporter = AuditExporter(settings, logging.getLogger("audit_test"))
    exported = exporter.export()
    content = exported.read_text(encoding="utf-8")
    assert "12345690" not in content
    assert "secret" not in content
    assert "Bearer123" not in content
    assert "***" in content


def test_export_safe_failure_without_key(tmp_path: Path) -> None:
    settings = build_settings(tmp_path)
    settings = settings.__class__(**{**settings.__dict__, "assistant_master_key": None})
    exporter = AuditExporter(settings, logging.getLogger("audit_test"))
    with pytest.raises(RuntimeError, match="ASSISTANT_MASTER_KEY ausente"):
        exporter.export()


def test_export_fails_safely_with_invalid_key(tmp_path: Path) -> None:
    settings = build_settings(tmp_path)
    security = SecurityManager(settings)
    security.audit_event("test", {"value": "ok"})
    wrong_settings = build_settings(tmp_path, master_key="wrong-master-key")
    exporter = AuditExporter(wrong_settings, logging.getLogger("audit_test"))
    with pytest.raises(RuntimeError, match="Chave invalida ou auditoria corrompida"):
        exporter.export()
