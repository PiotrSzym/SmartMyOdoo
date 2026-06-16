"""FIX-03: throttling żądań (rate-limit) — sliding window, reużywalny.

Inna semantyka niż _AuthRateLimiter (lockout dla logowania). Tu: ogranicz N żądań/okno
per tożsamość, zwróć info „przekroczono" (caller → HTTP 429 + Retry-After), bez trwałej blokady.

- Z Redisem (multi-worker): licznik INCR + EXPIRE na oknie (sliding-window-counter).
- Bez Redisa (testy/dev/single-proces): fallback proces-lokalny (znaczniki czasu w oknie).
Błędy Redisa → degradacja do trybu proces-lokalnego (nigdy nie wywala requestu).
"""

import logging
import os
import threading
import time
from typing import Any, Optional

logger = logging.getLogger(__name__)

# proces-lokalne okna: key -> list[monotonic timestamps]
_local: dict = {}
_guard = threading.Lock()


class RateLimiter:
    def __init__(
        self,
        max_requests: int = 30,
        window_s: int = 60,
        redis_url: Optional[str] = None,
        redis_client: Optional[Any] = None,
    ):
        self.max = max(1, int(max_requests))
        self.window = max(1, int(window_s))
        self._redis_url = redis_url
        self._redis = redis_client
        self._redis_checked = redis_client is not None

    def _get_redis(self) -> Optional[Any]:
        if self._redis_checked:
            return self._redis
        self._redis_checked = True
        if not self._redis_url:
            self._redis = None
            return None
        try:
            import redis  # type: ignore[import-untyped]

            client = redis.Redis.from_url(
                self._redis_url, socket_connect_timeout=0.5, socket_timeout=0.5
            )
            client.ping()
            self._redis = client
        except Exception as e:  # noqa: BLE001
            logger.warning(
                f"[ratelimit] Redis niedostępny ({e}) — fallback proces-lokalny."
            )
            self._redis = None
        return self._redis

    def allow(self, key: str) -> bool:
        """True = żądanie dozwolone; False = przekroczono limit w bieżącym oknie."""
        r = self._get_redis()
        if r is not None:
            full = f"rl:{key}"
            try:
                cnt = r.incr(full)
                if cnt == 1:
                    r.expire(full, self.window)
                return cnt <= self.max
            except Exception as e:  # noqa: BLE001
                logger.warning(
                    f"[ratelimit] Redis błąd ({e}) — fallback proces-lokalny."
                )

        now = time.monotonic()
        with _guard:
            arr = [t for t in _local.get(key, []) if now - t < self.window]
            if len(arr) >= self.max:
                _local[key] = arr
                return False
            arr.append(now)
            _local[key] = arr
            return True

    @property
    def retry_after(self) -> int:
        return self.window


# Limiter dla endpointów czatu (konfigurowalny ENV). Redis z REDIS_URL lub fallback.
chat_limiter = RateLimiter(
    max_requests=int(os.environ.get("CHAT_RATE_MAX", "30")),
    window_s=int(os.environ.get("CHAT_RATE_WINDOW_S", "60")),
    redis_url=os.environ.get("REDIS_URL"),
)
