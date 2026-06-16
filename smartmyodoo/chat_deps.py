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
