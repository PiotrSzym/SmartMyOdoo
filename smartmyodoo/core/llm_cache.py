"""FIX-02 S5.1: cache odpowiedzi LLM (redukcja kosztów/latencji).

Interfejs cache = obiekt z get(key)->Optional[Any] i set(key, value)->None.
- InMemoryLLMCache: prosty cache procesowy (deduplikacja identycznych zapytań w sesji).
- RedisLLMCache: rozproszony cache (pickle, TTL); best-effort — błędy Redisa są no-op.

Klucz budowany z (model, messages, tools) — identyczne wejście => trafienie w cache.
Cache jest OPCJONALNY (domyślnie wyłączony w kliencie) — brak zmiany zachowania bez wstrzyknięcia.
"""

import hashlib
import json
import logging
import pickle  # nosec B403 — serializacja WŁASNYCH odpowiedzi do naszego Redisa (dane zaufane)
from collections import OrderedDict
from typing import Any, List, Dict, Optional

logger = logging.getLogger(__name__)


def make_cache_key(
    model: str,
    messages: List[Dict[str, Any]],
    tools: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """Deterministyczny klucz z modelu + wiadomości + narzędzi (sha256)."""
    payload = json.dumps(
        {"model": model, "messages": messages, "tools": tools},
        sort_keys=True,
        default=str,
    )
    return "llm:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


class InMemoryLLMCache:
    """Cache procesowy z limitem rozmiaru (LRU). Idealny do dedupu w obrębie sesji/testów."""

    def __init__(self, max_size: int = 256):
        self.max_size = max_size
        self._store: "OrderedDict[str, Any]" = OrderedDict()

    def get(self, key: str) -> Optional[Any]:
        if key not in self._store:
            return None
        self._store.move_to_end(key)  # LRU touch
        return self._store[key]

    def set(self, key: str, value: Any) -> None:
        self._store[key] = value
        self._store.move_to_end(key)
        while len(self._store) > self.max_size:
            self._store.popitem(last=False)


class RedisLLMCache:
    """Rozproszony cache na Redis (pickle + TTL). Błędy backendu są tolerowane (no-op)."""

    def __init__(self, redis_client: Any, ttl_seconds: int = 3600):
        self.redis = redis_client
        self.ttl = ttl_seconds

    def get(self, key: str) -> Optional[Any]:
        try:
            raw = self.redis.get(key)
            # nosec B301 — odczyt z naszego Redisa (zapis tylko przez .set niżej); dane zaufane
            return pickle.loads(raw) if raw else None  # nosec B301
        except Exception as e:  # noqa: BLE001 — cache nie może wywalić requestu
            logger.warning(f"[LLM cache] odczyt Redis nieudany: {e}")
            return None

    def set(self, key: str, value: Any) -> None:
        try:
            self.redis.set(key, pickle.dumps(value), ex=self.ttl)
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[LLM cache] zapis Redis nieudany: {e}")
