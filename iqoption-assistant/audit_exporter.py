from __future__ import annotations

import json
import logging
import re
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

from config import Settings
from security import _derive_key


class AuditExporter:
    _patterns = [
        re.compile(r"(ASSISTANT_PIN=)([^\s]+)", re.IGNORECASE),
        re.compile(r"(ASSISTANT_MASTER_KEY=)([^\s]+)", re.IGNORECASE),
        re.compile(r"(token=)([^\s]+)", re.IGNORECASE),
        re.compile(r"(authorization[:=]\s*)([^\s]+)", re.IGNORECASE),
        re.compile(r"(cookie[:=]\s*)([^\s]+)", re.IGNORECASE),
        re.compile(r"(password=)([^\s]+)", re.IGNORECASE),
        re.compile(r"(senha=)([^\s]+)", re.IGNORECASE),
    ]

    def __init__(self, settings: Settings, logger: logging.Logger) -> None:
        self.settings = settings
        self.logger = logger

    def export(self, destination: Path | None = None) -> Path:
        if not self.settings.assistant_master_key:
            raise RuntimeError("ASSISTANT_MASTER_KEY ausente.")
        target = destination or (self.settings.logs_dir / "audit.exported.log")
        if not self.settings.encrypted_audit_file.exists():
            target.write_text("", encoding="utf-8")
            return target
        fernet = Fernet(_derive_key(self.settings.assistant_master_key))
        lines: list[str] = []
        for raw_line in self.settings.encrypted_audit_file.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line:
                continue
            try:
                payload = fernet.decrypt(line.encode("utf-8")).decode("utf-8")
            except InvalidToken as exc:
                raise RuntimeError("Chave invalida ou auditoria corrompida.") from exc
            lines.append(self._mask_sensitive(payload))
        target.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
        return target

    def _mask_sensitive(self, payload: str) -> str:
        masked = payload
        for pattern in self._patterns:
            masked = pattern.sub(r"\1***", masked)
        try:
            obj = json.loads(masked)
            return json.dumps(obj, ensure_ascii=True)
        except json.JSONDecodeError:
            return masked
