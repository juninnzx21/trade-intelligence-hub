from __future__ import annotations

from dataclasses import dataclass
import hashlib
import hmac
import json
import logging
import os

try:
    import bcrypt
except ModuleNotFoundError:
    bcrypt = None

from config import Settings


@dataclass(frozen=True)
class PinStatus:
    validated: bool
    blocked: bool
    remaining_attempts: int


class PinGuard:
    def __init__(self, settings: Settings, logger: logging.Logger) -> None:
        self.settings = settings
        self.logger = logger
        self._validated = False
        self._attempts_used = 0
        self._blocked = False

    def ensure_pin_hash(self) -> None:
        if self.settings.pin_hash_file.exists():
            return
        if not self.settings.assistant_pin:
            raise RuntimeError("ASSISTANT_PIN ausente.")
        payload = self._hash_pin(self.settings.assistant_pin)
        self.settings.pin_hash_file.write_text(json.dumps(payload, ensure_ascii=True), encoding="utf-8")
        self.logger.info("Hash seguro do PIN gerado localmente.")

    def validate_pin(self, pin: str) -> bool:
        if self._blocked:
            self.logger.warning("Tentativa de validacao de PIN com sessao bloqueada.")
            return False
        self.ensure_pin_hash()
        payload = json.loads(self.settings.pin_hash_file.read_text(encoding="utf-8"))
        ok = self._verify_pin(pin, payload)
        if ok:
            self._validated = True
            self._attempts_used = 0
            self.logger.info("PIN validado com sucesso.")
            return True
        self._attempts_used += 1
        self.logger.warning("Falha na validacao do PIN. Tentativas restantes: %s", self.remaining_attempts())
        if self._attempts_used >= self.settings.pin_max_attempts:
            self._blocked = True
            self.logger.error("PIN bloqueado por excesso de tentativas.")
        return False

    def is_validated(self) -> bool:
        return self._validated and not self._blocked

    def reset_session_validation(self) -> None:
        self._validated = False

    def remaining_attempts(self) -> int:
        return max(self.settings.pin_max_attempts - self._attempts_used, 0)

    def status(self) -> PinStatus:
        return PinStatus(validated=self.is_validated(), blocked=self._blocked, remaining_attempts=self.remaining_attempts())

    def _hash_pin(self, pin: str) -> dict[str, str]:
        if bcrypt is not None:
            hashed = bcrypt.hashpw(pin.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
            return {"scheme": "bcrypt", "hash": hashed}
        salt = os.urandom(16)
        derived = hashlib.pbkdf2_hmac("sha256", pin.encode("utf-8"), salt, 200_000)
        return {"scheme": "pbkdf2", "salt": salt.hex(), "hash": derived.hex(), "iterations": "200000"}

    def _verify_pin(self, pin: str, payload: dict[str, str]) -> bool:
        scheme = payload.get("scheme", "")
        if scheme == "bcrypt":
            if bcrypt is None:
                raise RuntimeError("Hash bcrypt encontrado, mas bcrypt nao esta instalado.")
            return bcrypt.checkpw(pin.encode("utf-8"), payload["hash"].encode("utf-8"))
        if scheme == "pbkdf2":
            salt = bytes.fromhex(payload["salt"])
            iterations = int(payload.get("iterations", "200000"))
            derived = hashlib.pbkdf2_hmac("sha256", pin.encode("utf-8"), salt, iterations)
            return hmac.compare_digest(derived.hex(), payload["hash"])
        raise RuntimeError("Formato de hash do PIN invalido.")
