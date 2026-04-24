from __future__ import annotations

from base64 import urlsafe_b64encode
from functools import lru_cache
from hashlib import sha256

from cryptography.fernet import Fernet

from app.core.config import get_settings


@lru_cache
def get_fernet() -> Fernet:
    settings = get_settings()
    secret = settings.secret_key or "market-decision-ai-dev-secret"
    digest = sha256(secret.encode("utf-8")).digest()
    return Fernet(urlsafe_b64encode(digest))


def encrypt_secret(value: str) -> str:
    return get_fernet().encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_secret(value: str) -> str:
    return get_fernet().decrypt(value.encode("utf-8")).decode("utf-8")
