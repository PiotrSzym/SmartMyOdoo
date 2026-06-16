"""FIX-02 S5.2: distributed lock (anty-TOCTOU) na sekcje krytyczne (np. approve propozycji).

- Z Redisem: `SET key token NX PX ttl` + bezpieczne zwolnienie (usuń tylko jeśli token nasz).
- Bez Redisa (testy/dev/single-proces): fallback na proces-lokalny `threading.Lock` per klucz,
  co serializuje równoległe żądania w obrębie procesu.

Użycie:
    with proposal_lock.acquire(f"proposal:approve:{pid}"):
        ...sekcja krytyczna...
"""

import os
import threading
import time
import uuid
from contextlib import contextmanager
from typing import Any, Optional

import logging

logger = logging.getLogger(__name__)

# Rejestr proces-lokalnych zamków (fallback bez Redisa)
_local_locks: dict = {}
_local_guard = threading.Lock()

# Lua: zwolnij tylko jeśli wartość == nasz token (brak zwolnienia cudzego locka)
_RELEASE_LUA = (
    "if redis.call('get', KEYS[1]) == ARGV[1] "
    "then return redis.call('del', KEYS[1]) else return 0 end"
)


class LockTimeout(Exception):
    """Nie udało się zdobyć locka w zadanym czasie."""


class DistributedLock:
    def __init__(
        self, redis_url: Optional[str] = None, redis_client: Optional[Any] = None
    ):
        self._redis_url = redis_url
        self._redis = redis_client
        self._redis_checked = redis_client is not None

    def _get_redis(self) -> Optional[Any]:
        """Leniwie łączy z Redisem (sync). Przy braku/awarii → None (fallback proces-lokalny)."""
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
        except Exception as e:  # noqa: BLE001 — brak Redisa = degradacja do proces-lokalnego
            logger.warning(f"[lock] Redis niedostępny ({e}) — fallback proces-lokalny.")
            self._redis = None
        return self._redis

    @contextmanager
    def acquire(self, key: str, ttl_ms: int = 10000, timeout: float = 5.0):
        redis_client = self._get_redis()
        if redis_client is not None:
            token = uuid.uuid4().hex
            deadline = time.monotonic() + timeout
            acquired = False
            while time.monotonic() < deadline:
                if redis_client.set(key, token, nx=True, px=ttl_ms):
                    acquired = True
                    break
                time.sleep(0.05)
            if not acquired:
                raise LockTimeout(f"Nie zdobyto locka Redis dla {key}")
            try:
                yield
            finally:
                try:
                    redis_client.eval(_RELEASE_LUA, 1, key, token)
                except Exception as e:  # noqa: BLE001
                    logger.warning(f"[lock] zwolnienie Redis nieudane dla {key}: {e}")
        else:
            with _local_guard:
                lk = _local_locks.setdefault(key, threading.Lock())
            if not lk.acquire(timeout=timeout):
                raise LockTimeout(f"Nie zdobyto locka proces-lokalnego dla {key}")
            try:
                yield
            finally:
                lk.release()


# Domyślny lock dla propozycji — Redis z ENV (multi-proces) lub fallback proces-lokalny.
proposal_lock = DistributedLock(redis_url=os.environ.get("REDIS_URL"))
