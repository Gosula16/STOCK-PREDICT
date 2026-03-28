"""Trading kill-switch and shared flags (Redis if configured, else in-process)."""

from __future__ import annotations

import redis

from app.config import get_settings


class StateStore:
    def __init__(self) -> None:
        self._redis: redis.Redis | None = None
        url = get_settings().redis_url
        if url:
            self._redis = redis.from_url(url, decode_responses=True)
        self._local_trading_enabled = True

    def is_trading_enabled(self) -> bool:
        if self._redis:
            v = self._redis.get("rentai:trading_enabled")
            if v is None:
                return True
            return v.lower() in ("1", "true", "yes")
        return self._local_trading_enabled

    def set_trading_enabled(self, enabled: bool) -> None:
        if self._redis:
            self._redis.set("rentai:trading_enabled", "true" if enabled else "false")
        else:
            self._local_trading_enabled = enabled


_store: StateStore | None = None


def get_state_store() -> StateStore:
    global _store
    if _store is None:
        _store = StateStore()
    return _store
