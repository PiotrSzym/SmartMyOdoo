"""S1.3 (dowód): rate-limit/lockout logowania + CORS bez '*' (jawne originy)."""

from fastapi.testclient import TestClient

from smartmyodoo import api
from smartmyodoo.api import _AuthRateLimiter


def test_auth_rate_limiter_locks_after_max():
    rl = _AuthRateLimiter(max_attempts=3, window_seconds=300)
    assert rl.is_locked("1.2.3.4") is False
    for _ in range(3):
        rl.record_failure("1.2.3.4")
    assert rl.is_locked("1.2.3.4") is True  # lockout po przekroczeniu prób
    rl.reset("1.2.3.4")
    assert rl.is_locked("1.2.3.4") is False  # reset po udanym logowaniu


def test_cors_rejects_unknown_origin_allows_known():
    client = TestClient(api.app)

    evil = client.options(
        "/api/auth",
        headers={
            "Origin": "http://evil.example.com",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert evil.headers.get("access-control-allow-origin") != "http://evil.example.com"

    ok = client.options(
        "/api/auth",
        headers={
            "Origin": "http://127.0.0.1:8000",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert ok.headers.get("access-control-allow-origin") == "http://127.0.0.1:8000"
