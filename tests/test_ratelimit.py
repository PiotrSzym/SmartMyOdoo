"""FIX-03: testy rate-limitera + wpięcia effective_model/cache w handlery czatu."""

from pathlib import Path

from smartmyodoo.core.ratelimit import RateLimiter

_CHAT = (
    Path(__file__).resolve().parents[1] / "smartmyodoo" / "api_routers" / "chat.py"
).read_text(encoding="utf-8")


def test_ratelimiter_allows_then_blocks():
    rl = RateLimiter(max_requests=3, window_s=60)  # bez Redisa → proces-lokalny
    k = "ws:test-a"
    assert [rl.allow(k) for _ in range(3)] == [True, True, True]
    assert rl.allow(k) is False  # 4. żądanie przekracza limit


def test_ratelimiter_keys_independent():
    rl = RateLimiter(max_requests=1, window_s=60)
    assert rl.allow("ws:a") is True
    assert rl.allow("ws:b") is True  # inny klucz — własne okno
    assert rl.allow("ws:a") is False


def test_ratelimiter_window_reset():
    # okno 0s (=1 po clamp) — kolejne wywołania szybko, ale sprawdzamy że licznik działa
    rl = RateLimiter(max_requests=2, window_s=1)
    assert rl.allow("ws:r") and rl.allow("ws:r")
    assert rl.allow("ws:r") is False


def test_chat_handlers_wire_followups():
    """Strażnik: handlery czatu używają rate-limit, effective_model i cache (FIX-03)."""
    assert "_enforce_chat_rate(" in _CHAT  # rate-limit w handle_chat/run_pipeline
    assert "chat_limiter.allow(" in _CHAT  # WS + helper
    assert "effective_model(" in _CHAT  # model wg polityki + budżet
    assert "get_llm_cache()" in _CHAT  # cache wpięty
    assert "read_only" in _CHAT  # cache tylko dla read-only (świeżość)
    assert "status_code=429" in _CHAT  # 429 przy przekroczeniu
