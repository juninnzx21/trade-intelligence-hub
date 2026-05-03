from __future__ import annotations

from base64 import urlsafe_b64encode
from datetime import datetime
import hashlib
import json
import logging
import os
from pathlib import Path
import re

from cryptography.fernet import Fernet

from config import Settings


def _derive_key(master_key: str) -> bytes:
    digest = hashlib.sha256(master_key.encode("utf-8")).digest()
    return urlsafe_b64encode(digest)


class RedactingFilter(logging.Filter):
    _patterns = [
        re.compile(r"(ASSISTANT_PIN=)([^\s]+)", re.IGNORECASE),
        re.compile(r"(ASSISTANT_MASTER_KEY=)([^\s]+)", re.IGNORECASE),
        re.compile(r"(token=)([^\s]+)", re.IGNORECASE),
        re.compile(r"(authorization[:=]\s*)([^\s]+)", re.IGNORECASE),
        re.compile(r"(cookie[:=]\s*)([^\s]+)", re.IGNORECASE),
        re.compile(r"(password=)([^\s]+)", re.IGNORECASE),
        re.compile(r"(senha=)([^\s]+)", re.IGNORECASE),
    ]

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        for pattern in self._patterns:
            message = pattern.sub(r"\1***", message)
        record.msg = message
        record.args = ()
        return True


class SecurityManager:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._fernet: Fernet | None = None
        if settings.enable_local_encryption and settings.assistant_master_key:
            self._fernet = Fernet(_derive_key(settings.assistant_master_key))

    @property
    def encryption_ready(self) -> bool:
        return self._fernet is not None

    def harden_local_storage(self) -> None:
        for path in (self.settings.storage_dir, self.settings.logs_dir, self.settings.chrome_user_data_dir):
            path.mkdir(parents=True, exist_ok=True)
            try:
                os.chmod(path, 0o700)
            except OSError:
                pass

    def audit_event(self, event_type: str, payload: dict[str, object]) -> None:
        envelope = {
            "ts": datetime.now().isoformat(),
            "event_type": event_type,
            "payload": payload,
        }
        line = json.dumps(envelope, ensure_ascii=True)
        if self._fernet is None:
            self.settings.encrypted_audit_file.write_text(
                self.settings.encrypted_audit_file.read_text(encoding="utf-8") + line + "\n"
                if self.settings.encrypted_audit_file.exists()
                else line + "\n",
                encoding="utf-8",
            )
            return
        token = self._fernet.encrypt(line.encode("utf-8")).decode("utf-8")
        with self.settings.encrypted_audit_file.open("a", encoding="utf-8") as handle:
            handle.write(token + "\n")

    def warn_if_unsealed(self, logger: logging.Logger) -> None:
        if not self.settings.enable_local_encryption:
            logger.warning("Criptografia local desativada por configuracao.")
            return
        if not self.settings.assistant_master_key:
            logger.warning("ASSISTANT_MASTER_KEY ausente. Auditoria local ficara sem sigilo forte em repouso.")
