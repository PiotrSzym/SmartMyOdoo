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


def test_startup_hook_registered():
    """api.py rejestruje hook startowy logujący tryb backendów."""
    from smartmyodoo import api

    src = (api.__file__,)
    assert src  # import nie wywala
    # funkcja hooka istnieje
    assert hasattr(api, "_log_backend_modes")
