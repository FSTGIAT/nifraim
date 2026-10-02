"""Per-user answer/metric cache.

Key = (user_id, data_version, *key). `data_version` lives on users.ai_data_version
and is bumped by every ingest path (agent/versioning.py), so a stale answer can't
survive new data — TTL is only a backstop. In-process LRU: production runs one
uvicorn worker; the version is in the DB, so a worker on another process (the
local worker ingests straight into prod) still invalidates us.
"""
from __future__ import annotations

import time
from collections import OrderedDict
from typing import Any

MAX_ITEMS = 2000
_store: "OrderedDict[tuple, tuple[float, Any]]" = OrderedDict()


def _k(user_id, version: int, key: tuple) -> tuple:
    return (str(user_id), int(version or 0), *key)


def get(user_id, version: int, key: tuple):
    k = _k(user_id, version, key)
    hit = _store.get(k)
    if not hit:
        return None
    exp, val = hit
    if exp < time.monotonic():
        _store.pop(k, None)
        return None
    _store.move_to_end(k)
    return val


def put(user_id, version: int, key: tuple, value, ttl: int = 600) -> None:
    _store[_k(user_id, version, key)] = (time.monotonic() + ttl, value)
    _store.move_to_end(_k(user_id, version, key))
    while len(_store) > MAX_ITEMS:
        _store.popitem(last=False)


def drop_user(user_id) -> None:
    u = str(user_id)
    for k in [k for k in _store if k[0] == u]:
        _store.pop(k, None)
