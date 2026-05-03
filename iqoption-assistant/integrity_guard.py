from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
from pathlib import Path

from config import Settings


SOURCE_MONITORED_FILES = [
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

DIST_MONITORED_FILES = [
    "iqoption-assistant.exe",
    "README.md",
    ".env.example",
    "_internal/ui",
    "_internal/PySide6",
    "_internal/playwright",
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
        profile, targets = self._resolve_targets()
        files = {name: self._entry_digest(self.settings.root_dir / name) for name in targets}
        payload = {
            "generated_at": datetime.now().isoformat(),
            "profile": profile,
            "files": files,
        }
        self.settings.integrity_manifest.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")
        return self.settings.integrity_manifest

    def check_integrity(self) -> IntegrityCheckResult:
        if not self.settings.integrity_manifest.exists():
            return IntegrityCheckResult(False, "NAO GERADA", ["Manifesto de integridade ausente."])

        payload = json.loads(self.settings.integrity_manifest.read_text(encoding="utf-8"))
        manifest_profile = payload.get("profile")
        current_profile, targets = self._resolve_targets()
        expected = payload.get("files", {})
        details: list[str] = []
        ok = True

        if manifest_profile and manifest_profile != current_profile:
            ok = False
            details.append(f"Manifesto incompatível com o perfil atual: {manifest_profile} != {current_profile}")

        for name in targets:
            path = self.settings.root_dir / name
            if not path.exists():
                ok = False
                details.append(f"Arquivo ausente: {name}")
                continue
            current_hash = self._entry_digest(path)
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

    def _resolve_targets(self) -> tuple[str, list[str]]:
        root = self.settings.root_dir
        if (root / "iqoption-assistant.exe").exists() and (root / "_internal").exists():
            return "dist", DIST_MONITORED_FILES
        return "source", SOURCE_MONITORED_FILES

    @staticmethod
    def _entry_digest(path: Path) -> str:
        if path.is_dir():
            digest = hashlib.sha256()
            for child in sorted(item for item in path.rglob("*") if item.is_file()):
                digest.update(str(child.relative_to(path)).encode("utf-8"))
                digest.update(IntegrityGuard._file_sha256(child).encode("utf-8"))
            return digest.hexdigest()
        return IntegrityGuard._file_sha256(path)

    @staticmethod
    def _file_sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(65_536), b""):
                digest.update(chunk)
        return digest.hexdigest()

