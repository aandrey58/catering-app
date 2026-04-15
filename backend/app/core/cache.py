import time
from threading import Lock


class TTLCache:
    def __init__(self, ttl_seconds: int = 60) -> None:
        self._ttl_seconds = ttl_seconds
        self._storage: dict[str, tuple[float, object]] = {}
        self._lock = Lock()

    def get(self, key: str):
        with self._lock:
            cached = self._storage.get(key)
            if not cached:
                return None

            expires_at, value = cached
            if time.time() >= expires_at:
                self._storage.pop(key, None)
                return None
            return value

    def set(self, key: str, value: object) -> None:
        with self._lock:
            expires_at = time.time() + self._ttl_seconds
            self._storage[key] = (expires_at, value)

    def invalidate_prefix(self, prefix: str) -> None:
        with self._lock:
            stale_keys = [key for key in self._storage if key.startswith(prefix)]
            for key in stale_keys:
                self._storage.pop(key, None)
