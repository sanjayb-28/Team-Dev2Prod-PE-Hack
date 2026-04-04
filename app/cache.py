import json
import os
from typing import Any

from flask import Flask
from redis import Redis
from redis.exceptions import RedisError


_cache_client: Redis | None = None
_cache_enabled = False
URL_CACHE_PREFIX = "urls-api"


def init_cache(app: Flask):
    global _cache_client, _cache_enabled

    redis_url = os.environ.get("REDIS_URL")
    if not redis_url:
        _cache_client = None
        _cache_enabled = False
        app.config["CACHE_MODE"] = "disabled"
        return

    _cache_client = Redis.from_url(redis_url, decode_responses=True)
    _cache_enabled = True
    app.config["CACHE_MODE"] = "redis"


def cache_mode() -> str:
    return "redis" if _cache_enabled and _cache_client is not None else "disabled"


def cache_status_header(status: str) -> str:
    return status.upper()


def get_cached_json(key: str) -> tuple[Any | None, str]:
    if not _cache_enabled or _cache_client is None:
        return None, "bypass"

    try:
        cached = _cache_client.get(key)
    except RedisError:
        return None, "bypass"

    if cached is None:
        return None, "miss"

    try:
        return json.loads(cached), "hit"
    except json.JSONDecodeError:
        return None, "miss"


def set_cached_json(key: str, payload: Any, ttl_seconds: int = 90):
    if not _cache_enabled or _cache_client is None:
        return

    try:
        _cache_client.setex(key, ttl_seconds, json.dumps(payload))
    except RedisError:
        return


def invalidate_cache_prefix(prefix: str):
    if not _cache_enabled or _cache_client is None:
        return

    try:
        keys = list(_cache_client.scan_iter(match=f"{prefix}*"))
        if keys:
            _cache_client.delete(*keys)
    except RedisError:
        return


def url_cache_key(url_id: int | None = None, *, user_id: int | None = None, is_active: bool | None = None) -> str:
    if url_id is not None:
        return f"{URL_CACHE_PREFIX}:detail:{url_id}"

    filters = [
        f"user:{user_id if user_id is not None else 'all'}",
        f"active:{is_active if is_active is not None else 'all'}",
    ]
    return f"{URL_CACHE_PREFIX}:list:{':'.join(filters)}"
