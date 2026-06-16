"""FIX-02 / S3.1: dowód, że domeny auth/secrets są obsługiwane przez wydzielone routery.

Strażnik single-source: endpoint funkcje żyją w api_routers.{auth,secrets}, nie w api.py.
Gdyby ktoś przywrócił handler do God Module, ten test zapali się na czerwono.
"""

from smartmyodoo.api import app

# ścieżka -> moduł, w którym MUSI żyć handler po S3.1
_EXPECTED_MODULE = {
    "/api/status": "smartmyodoo.api_routers.auth",
    "/api/init": "smartmyodoo.api_routers.auth",
    "/api/auth": "smartmyodoo.api_routers.auth",
    "/api/change-pin": "smartmyodoo.api_routers.auth",
    "/api/secrets": "smartmyodoo.api_routers.secrets",
    "/api/secrets/{key_name}": "smartmyodoo.api_routers.secrets",
    "/api/secrets/{key_name}/restore": "smartmyodoo.api_routers.secrets",
    "/api/secrets/{key_name}/permanent": "smartmyodoo.api_routers.secrets",
    "/api/secrets/by-workspace/{ws_id}": "smartmyodoo.api_routers.secrets",
}


def _routes_by_path():
    out = {}
    for r in app.routes:
        if hasattr(r, "path") and hasattr(r, "endpoint"):
            out.setdefault(r.path, []).append(r)
    return out


def test_auth_secrets_routes_served_by_extracted_routers():
    routes = _routes_by_path()
    for path, expected_mod in _EXPECTED_MODULE.items():
        assert path in routes, f"brak trasy {path}"
        mods = {r.endpoint.__module__ for r in routes[path]}
        assert mods == {expected_mod}, (
            f"{path} obsługiwane przez {mods}, oczekiwano {{{expected_mod}}} "
            f"(handler powinien żyć w wydzielonym routerze, nie w api.py)"
        )


def test_auth_rate_limiter_still_importable_from_api():
    """Kompatybilność wsteczna: _AuthRateLimiter re-eksportowany z api (test_security_s13)."""
    from smartmyodoo.api import _AuthRateLimiter
    from smartmyodoo.api_routers.auth import _AuthRateLimiter as _Canonical

    assert _AuthRateLimiter is _Canonical
