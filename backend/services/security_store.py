from __future__ import annotations

import time
import threading
from typing import Optional

from ..config import get_settings


class InMemoryStore:
    def __init__(self):
        self._lock = threading.Lock()
        self._data: dict[str, tuple[float, str]] = {}

    def set_if_not_exists(self, key: str, value: str, ttl_seconds: int) -> bool:
        now = time.time()
        with self._lock:
            self._cleanup(now)
            if key in self._data:
                return False
            self._data[key] = (now + ttl_seconds, value)
            return True

    def get(self, key: str) -> Optional[str]:
        now = time.time()
        with self._lock:
            self._cleanup(now)
            if key not in self._data:
                return None
            return self._data[key][1]

    def incr(self, key: str, ttl_seconds: int) -> int:
        now = time.time()
        with self._lock:
            self._cleanup(now)
            if key not in self._data:
                self._data[key] = (now + ttl_seconds, "1")
                return 1
            exp, val = self._data[key]
            new_val = str(int(val) + 1)
            self._data[key] = (exp, new_val)
            return int(new_val)

    def _cleanup(self, now: float) -> None:
        expired = [k for k, (exp, _) in self._data.items() if exp <= now]
        for k in expired:
            self._data.pop(k, None)


class SecurityStore:
    def __init__(self):
        self.settings = get_settings()
        self._redis = None
        self._mem = InMemoryStore()
        self._init_redis()

    def _init_redis(self) -> None:
        try:
            import redis  # type: ignore

            self._redis = redis.Redis.from_url(self.settings.REDIS_URL)
            self._redis.ping()
        except Exception:
            self._redis = None
            if self.settings.REDIS_REQUIRED:
                raise RuntimeError("Redis required but unavailable")

    def set_if_not_exists(self, key: str, value: str, ttl_seconds: int) -> bool:
        if self._redis is not None:
            return bool(self._redis.set(name=key, value=value, ex=ttl_seconds, nx=True))
        return self._mem.set_if_not_exists(key, value, ttl_seconds)

    def get(self, key: str) -> Optional[str]:
        if self._redis is not None:
            val = self._redis.get(key)
            return val.decode("utf-8") if val else None
        return self._mem.get(key)

    def incr(self, key: str, ttl_seconds: int) -> int:
        if self._redis is not None:
            pipe = self._redis.pipeline()
            pipe.incr(key, 1)
            pipe.expire(key, ttl_seconds)
            value, _ = pipe.execute()
            return int(value)
        return self._mem.incr(key, ttl_seconds)


security_store = SecurityStore()
