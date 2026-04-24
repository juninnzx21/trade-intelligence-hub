from __future__ import annotations

import json
import logging
import sys
from datetime import datetime
from uuid import uuid4

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


def configure_logging() -> None:
    root = logging.getLogger()
    if root.handlers:
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(message)s"))
    root.addHandler(handler)
    root.setLevel(logging.INFO)


def log_event(level: str, event: str, **kwargs: object) -> None:
    logger = logging.getLogger("market_decision_ai")
    payload = {
        "ts": datetime.utcnow().isoformat(),
        "level": level.upper(),
        "event": event,
        **kwargs,
    }
    logger.log(getattr(logging, level.upper(), logging.INFO), json.dumps(payload, ensure_ascii=True))


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id") or str(uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["x-request-id"] = request_id
        return response
