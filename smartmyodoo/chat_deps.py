"""FIX-02 S3.1b: współdzielone zależności domeny chat (deps-module).

Dostarcza singletony, których potrzebują handlery chatu: `dispatcher` (router intencji)
i `get_pii()` (PiiMiddleware). Wydzielone z api.py, żeby router chatu (`api_routers/chat.py`)
NIE importował `api.py` — inaczej odtworzyłby cykl importów zlikwidowany w S3.4.

Zależy tylko od swarm/mcp — bez importu api.py ani routerów.
`api.py` re-eksportuje `dispatcher`/`get_pii` (jako `_get_pii`) dla kompatybilności wstecznej.
"""

import os
from typing import Any, Optional

from smartmyodoo.swarm.dispatcher import Dispatcher
from smartmyodoo.swarm import llm_client

# LLM Client: odczyt klucza z ENV (opcjonalnie wstrzyknięty przez Vault CLI)
_llm = llm_client.create_client(api_key=os.environ.get("OPENROUTER_KEY"))
dispatcher = Dispatcher(llm_client=_llm)

# S1.1: współdzielona instancja PiiMiddleware (mapping per workspace_id), lazy by nie ładować
# presidio przy imporcie modułu.
_pii_singleton: Optional[Any] = None


def get_pii() -> Any:
    global _pii_singleton
    if _pii_singleton is None:
        from smartmyodoo.mcp.pii_middleware import PiiMiddleware

        _pii_singleton = PiiMiddleware()
    return _pii_singleton


# FIX-03: współdzielony cache odpowiedzi LLM (S5.1). Redis gdy REDIS_URL, inaczej In-Memory.
# Wyłączalny: LLM_CACHE=off. UWAGA — wpinać tylko dla skilli read-only (świeżość danych live).
_llm_cache_singleton: Optional[Any] = None
_llm_cache_checked = False


def get_llm_cache() -> Any:
    global _llm_cache_singleton, _llm_cache_checked
    if _llm_cache_checked:
        return _llm_cache_singleton
    _llm_cache_checked = True
    if os.environ.get("LLM_CACHE", "on").lower() in ("off", "0", "false"):
        _llm_cache_singleton = None
        return None
    redis_url = os.environ.get("REDIS_URL")
    try:
        if redis_url:
            import redis  # type: ignore[import-untyped]

            from smartmyodoo.core.llm_cache import RedisLLMCache

            client = redis.Redis.from_url(
                redis_url, socket_connect_timeout=0.5, socket_timeout=0.5
            )
            client.ping()
            _llm_cache_singleton = RedisLLMCache(client)
            return _llm_cache_singleton
    except Exception:  # noqa: BLE001 — brak/awaria Redisa → cache In-Memory
        pass
    from smartmyodoo.core.llm_cache import InMemoryLLMCache

    _llm_cache_singleton = InMemoryLLMCache()
    return _llm_cache_singleton
