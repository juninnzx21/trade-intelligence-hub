from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
from pathlib import Path

from config import Settings


MONITORED_FILES = [
    "main.py",
    "auto_trader.py",
    "browser_controller.py",
    "risk_guard.py",
    "floating_stop.py",
    "signal_parser.py",
    "security.py",
    "pin_guard.py",
    "integrity_guard.py",
    "audit_exporter.py",
]


@dataclass(frozen=True)
class IntegrityCheckResult:
    ok: bool
    status: str
    details: list[str]


class IntegrityGuard:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def write_manifest(self) -> Path:
        files = {name: self._sha256(self.settings.root_dir / name) for name in MONITORED_FILES}
        payload = {"generated_at": datetime.now().isoformat(), "files": files}
        self.settings.integrity_manifest.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")
        return self.settings.integrity_manifest

    def check_integrity(self) -> IntegrityCheckResult:
        if not self.settings.integrity_manifest.exists():
            return IntegrityCheckResult(False, "NAO GERADA", ["Manifesto de integridade ausente."])
        payload = json.loads(self.settings.integrity_manifest.read_text(encoding="utf-8"))
        expected = payload.get("files", {})
        details: list[str] = []
        ok = True
        for name in MONITORED_FILES:
            path = self.settings.root_dir / name
            if not path.exists():
                ok = False
                details.append(f"Arquivo ausente: {name}")
                continue
            current_hash = self._sha256(path)
            expected_hash = expected.get(name)
            if expected_hash != current_hash:
                ok = False
                details.append(f"Hash divergente: {name}")
        status = "OK" if ok else "FALHA"
        if ok:
            details.append("Todos os arquivos monitorados conferem com o manifesto.")
        return IntegrityCheckResult(ok, status, details)

    def is_integrity_ok(self) -> bool:
        return self.check_integrity().ok

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(65_536), b""):
                digest.update(chunk)
        return digest.hexdigest()
