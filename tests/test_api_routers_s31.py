"""FIX-02 / S3.1: dowód, że domeny auth/secrets są obsługiwane przez wydzielone routery.

Strażnik single-source: endpoint funkcje żyją w api_routers.{auth,secrets}, nie w api.py.
Gdyby ktoś przywrócił handler do God Module, ten test zapali się na czerwono.
"""

from smartmyodoo.api import app
from smartmyodoo.api_routers import auth as auth_router_mod
from smartmyodoo.api_routers import secrets as secrets_router_mod

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


def _endpoint_modules_by_path():
    """Mapa: ścieżka -> {moduły handlerów} z WYDZIELONYCH routerów (auth/secrets).

    Introspekcja samych obiektów routerów, nie `app.routes` — odporna na zmianę modelu
    inkluzji w FastAPI >=0.137 (leniwe `_IncludedRouter`, które nie wystawia płaskich
    `APIRoute` z `.path` w `app.routes`). Sam fakt rejestracji tras w aplikacji
    sprawdzamy niżej przez publiczne, stabilne `app.openapi()["paths"]`.
    """
    out = {}
    for mod in (auth_router_mod, secrets_router_mod):
        for r in mod.router.routes:
            path = getattr(r, "path", None)
            endpoint = getattr(r, "endpoint", None)
            if path and endpoint is not None:
                out.setdefault(path, set()).add(endpoint.__module__)
    return out


def test_auth_secrets_routes_served_by_extracted_routers():
    registered = set(app.openapi()["paths"])  # publiczne API tras — stabilne między wersjami
    by_module = _endpoint_modules_by_path()
    for path, expected_mod in _EXPECTED_MODULE.items():
        assert path in registered, f"brak trasy {path} (nie zarejestrowana w app)"
        mods = by_module.get(path, set())
        assert mods == {expected_mod}, (
            f"{path} obsługiwane przez {mods}, oczekiwano {{{expected_mod}}} "
            f"(handler powinien żyć w wydzielonym routerze, nie w api.py)"
        )


def test_auth_rate_limiter_still_importable_from_api():
    """Kompatybilność wsteczna: _AuthRateLimiter re-eksportowany z api (test_security_s13)."""
    from smartmyodoo.api import _AuthRateLimiter
    from smartmyodoo.api_routers.auth import _AuthRateLimiter as _Canonical

    assert _AuthRateLimiter is _Canonical
