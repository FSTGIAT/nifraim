"""One shared asyncio Redis client for the calls plane (lazy — no Redis needed when CALLS_ENABLED is off)."""
from __future__ import annotations

import redis.asyncio as aioredis

from app.config import settings

_client: aioredis.Redis | None = None


def get_redis() -> aioredis.Redis:
    global _client
    if _client is None:
        _client = aioredis.from_url(settings.REDIS_URL, decode_responses=True, health_check_interval=30)
    return _client
