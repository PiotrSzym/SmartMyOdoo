"""SmartMyOdoo FastAPI — gateway.

FIX-02 (S3.1/S3.4): God Module rozbity na routery domenowe (api_routers/*) + deps-module
(api_deps, chat_deps). Ten plik tworzy `app`, montuje routery i UI oraz re-eksportuje
wybrane symbole dla kompatybilności wstecznej.
"""

import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from smartmyodoo.core.database import engine
from smartmyodoo.core import models as db_models

db_models.Base.metadata.create_all(bind=engine)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """RELEASE-01 T2: cykl życia aplikacji (zastępuje deprecated @app.on_event).

    Startup (przed `yield`): log trybu współdzielonego stanu (Redis vs proces-lokalny) —
    zachowuje zachowanie poprzedniego `on_event('startup')`. Schemat DB tworzony jest
    przy imporcie (`Base.metadata.create_all`), a migracje odpala alembic poza procesem
    aplikacji (DOCKER-01 / ADR-010), więc tu ich nie wołamy.

    Shutdown (po `yield`): graceful shutdown — log + zamknięcie puli połączeń silnika DB,
    by SIGTERM/stop kontenera kończył się czysto (US-REL-2).
    """
    from smartmyodoo.core.runtime_info import log_backend_modes

    log_backend_modes()
    try:
        yield
    finally:
        logger.info("[lifespan] Zamykanie aplikacji — graceful shutdown.")
        engine.dispose()


app = FastAPI(
    title="SmartMyVault API",
    description="FastAPI migration of Vault API",
    lifespan=lifespan,
)


# S1.3: jawna lista originów (koniec '*'+credentials, które echo'wało dowolny Origin).
# Konfiguracja przez CORS_ALLOWED_ORIGINS (CSV); domyślnie lokalny UI.
_cors_origins = [
    o.strip()
    for o in os.environ.get(
        "CORS_ALLOWED_ORIGINS", "http://127.0.0.1:8000,http://localhost:8000"
    ).split(",")
    if o.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# Re-eksporty dla kompatybilności wstecznej (kod/testy robią `from smartmyodoo.api import ...`).
# Auth (S3.4 deps-module):
from smartmyodoo.api_deps import get_auth_key, require_auth  # noqa: E402,F401

# Chat deps (S3.1b): dispatcher + PII singleton (alias _get_pii zachowany historycznie):
from smartmyodoo.chat_deps import (  # noqa: E402,F401
    dispatcher,
    get_pii as _get_pii,
)

# S3.1: routery domenowe wydzielone z God Module (przed catch-all mount /).
# FIX-02 S3.4: routery importują auth z api_deps — cykl zerwany, brak `# type: ignore`.
from smartmyodoo.api_routers.proposals import router as proposals_router  # noqa: E402
from smartmyodoo.api_routers.monitoring import router as monitoring_router  # noqa: E402
from smartmyodoo.api_routers.workspaces import router as workspaces_router  # noqa: E402
from smartmyodoo.api_routers.models import router as models_router  # noqa: E402
from smartmyodoo.api_routers.secrets import router as secrets_router  # noqa: E402
from smartmyodoo.api_routers.auth import router as auth_router  # noqa: E402
from smartmyodoo.api_routers.chat import router as chat_router  # noqa: E402

# FIX-02 S3.1: re-eksport dla kompatybilności (tests/test_security_s13.py importuje stąd).
from smartmyodoo.api_routers.auth import _AuthRateLimiter  # noqa: E402,F401

app.include_router(proposals_router)
app.include_router(monitoring_router)
app.include_router(workspaces_router)
app.include_router(models_router)
app.include_router(secrets_router)
app.include_router(auth_router)
app.include_router(chat_router)

ui_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ui")
app.mount("/", StaticFiles(directory=ui_dir, html=True), name="ui")


def start_server(port=8000):
    import uvicorn
    import webbrowser
    import threading
    import time

    url = f"http://127.0.0.1:{port}"
    print("==================================================")
    print(f"|  FastAPI Vault Server działa: {url} |")
    print("|  Proszę nie zamykać tej konsoli.               |")
    print("==================================================")

    def open_browser():
        time.sleep(1)
        webbrowser.open(url + "/")

    threading.Thread(target=open_browser, daemon=True).start()

    uvicorn.run("smartmyodoo.api:app", host="127.0.0.1", port=port, log_level="info")


if __name__ == "__main__":
    start_server()
