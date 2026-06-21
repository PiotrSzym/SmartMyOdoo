"""RELEASE-01 / T2: dowód, że app używa lifespan (nie deprecated on_event).

US-REL-2: serwer startuje/zamyka się czysto przez `lifespan` (@asynccontextmanager),
bez `DeprecationWarning` z `@app.on_event(...)`, a `/api/status` zwraca 200 po starcie
przez kontekst lifespan (TestClient jako context manager odpala startup/shutdown).
"""

import warnings

from fastapi.testclient import TestClient

from smartmyodoo.api import app


def test_app_has_lifespan_not_on_event():
    """Aplikacja MUSI mieć skonfigurowany lifespan (FastAPI ≥0.93), nie on_event.

    `on_event` jest deprecated od FastAPI 0.93 i emituje DeprecationWarning. Po migracji
    `app.router.lifespan_context` jest niedomyślny (ustawiony przez `lifespan=...`),
    a lista handlerów on_event (`on_startup`/`on_shutdown`) jest pusta.
    """
    # Brak zarejestrowanych handlerów on_event (startup/shutdown) — wszystko w lifespan.
    assert not app.router.on_startup, (
        "app.router.on_startup nie jest pusty — pozostał deprecated @app.on_event('startup')"
    )
    assert not app.router.on_shutdown, (
        "app.router.on_shutdown nie jest pusty — pozostał deprecated @app.on_event('shutdown')"
    )


def test_lifespan_startup_no_deprecation_warning_and_status_200():
    """Start przez lifespan (TestClient context) → brak DeprecationWarning + /api/status=200."""
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        # TestClient jako context manager odpala startup (lifespan) i shutdown.
        with TestClient(app) as client:
            resp = client.get("/api/status")
            assert resp.status_code == 200
            assert "initialized" in resp.json()

    on_event_deprecations = [
        w
        for w in caught
        if issubclass(w.category, DeprecationWarning)
        and "on_event" in str(w.message).lower()
    ]
    assert not on_event_deprecations, (
        f"Wykryto DeprecationWarning dot. on_event: "
        f"{[str(w.message) for w in on_event_deprecations]}"
    )
