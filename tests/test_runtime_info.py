"""Test logu trybu backendów (Redis vs proces-lokalny) + startup hook."""

from smartmyodoo.core import runtime_info


def test_redis_unreachable_without_url():
    assert runtime_info.redis_reachable(None) is False
    assert runtime_info.redis_reachable("") is False


def test_log_backend_modes_returns_false_without_redis(monkeypatch, caplog):
    monkeypatch.delenv("REDIS_URL", raising=False)
    import logging

    with caplog.at_level(logging.WARNING):
        assert runtime_info.log_backend_modes() is False
    assert any("PROCES-LOKALNY" in r.message for r in caplog.records)


def test_log_backend_modes_redis_set_but_down(monkeypatch, caplog):
    # nieosiągalny adres → degradacja, nie wyjątek
    monkeypatch.setenv("REDIS_URL", "redis://127.0.0.1:6390/0")
    assert runtime_info.log_backend_modes() is False


def test_startup_logs_backend_modes_via_lifespan():
    """api.py loguje tryb backendów na starcie przez lifespan (RELEASE-01 T2).

    Wcześniej była to funkcja `_log_backend_modes` pod `@app.on_event('startup')`
    (deprecated). Po migracji na `@asynccontextmanager lifespan` (US-REL-2) kontrakt
    jest ten sam — start aplikacji woła `runtime_info.log_backend_modes()` — ale realizuje
    go lifespan, NIE deprecated on_event. Dowód: lifespan ustawiony, on_event puste,
    a startup faktycznie woła log_backend_modes (TestClient context = uruchom lifespan).
    """
    from smartmyodoo import api

    assert api.__file__  # import nie wywala

    # 1. Lifespan ustawiony, deprecated on_event NIE używane.
    assert api.lifespan is not None
    assert not api.app.router.on_startup, "pozostał deprecated @app.on_event('startup')"
    assert not api.app.router.on_shutdown

    # 2. Startup przez lifespan faktycznie loguje tryb backendów (kontrakt zachowany).
    from unittest.mock import patch

    from fastapi.testclient import TestClient

    with patch("smartmyodoo.core.runtime_info.log_backend_modes") as mock_log:
        with TestClient(api.app):  # context manager odpala startup (lifespan)
            pass
        mock_log.assert_called_once()
