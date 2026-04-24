from __future__ import annotations

import json

from redis.exceptions import RedisError

from app.core.config import get_settings
from app.core.redis import get_redis
from app.schemas.analysis import LiveAssetBoardItem


LIVE_BOARD_CACHE_KEY = "market:live_board:latest"


def cache_live_board(board: list[LiveAssetBoardItem]) -> None:
    settings = get_settings()
    payload = json.dumps([item.model_dump(mode="json") for item in board], ensure_ascii=True)
    try:
        redis = get_redis()
        redis.set(LIVE_BOARD_CACHE_KEY, payload, ex=120)
        redis.publish(settings.redis_live_board_channel, payload)
    except RedisError:
        return


def get_cached_live_board() -> list[dict]:
    try:
        payload = get_redis().get(LIVE_BOARD_CACHE_KEY)
        return json.loads(payload) if payload else []
    except (RedisError, json.JSONDecodeError):
        return []
