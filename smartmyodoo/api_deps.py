"""FIX-02 S3.4: współdzielone zależności FastAPI (deps-module).

Wydzielone z `api.py`, żeby zerwać cykl importów: routery domenowe
(`api_routers/*`) potrzebują `require_auth`, a `api.py` importuje te routery.
Wcześniej routery robiły `from smartmyodoo.api import require_auth` — przy
uruchomieniu `python -m smartmyodoo.api` (moduł jako `__main__`) dawało to
ImportError (partially initialized module).

Ten moduł NIE importuje `api.py` ani żadnego routera — zależy tylko od `vault`.
`api.py` re-eksportuje te symbole dla kompatybilności wstecznej.
"""

from typing import Optional, Tuple

from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from smartmyodoo.vault import vault

# Pojedyncza instancja schematu Bearer (współdzielona przez api.py i routery).
security = HTTPBearer()


def get_auth_key(pwd: str) -> Tuple[Optional[bytes], Optional[str]]:
    """Zwraca (vault_key, rola) dla hasła: najpierw Master (admin), potem PIN (user)."""
    try:
        vk = vault.get_vault_key_from_master(pwd, exit_on_fail=False)
        return vk, "admin"
    except (vault.InvalidToken, ValueError):
        pass
    try:
        vk = vault.get_vault_key_from_pin(pwd, exit_on_fail=False)
        return vk, "user"
    except (vault.InvalidToken, ValueError):
        return None, None


def require_auth(
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> Tuple[bytes, str, str]:
    """Dependency FastAPI: waliduje Bearer i zwraca (vault_key, rola, hasło)."""
    pwd = credentials.credentials
    vk, role = get_auth_key(pwd)
    if not vk:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return vk, str(role), pwd
