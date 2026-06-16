"""FIX-02 S3.1: domena `auth` (status/init/auth/change-pin) wydzielona z api.py.

Zachowanie bez zmian — pełne ścieżki zachowane (router bez prefixu).
`_AuthRateLimiter` przeniesiony tu; api.py re-eksportuje go dla kompatybilności testów.
"""

import os
from typing import Dict, Tuple

from fastapi import APIRouter, Depends, HTTPException, Request

from smartmyodoo.vault import vault
from smartmyodoo.vault import schemas
from smartmyodoo.api_deps import get_auth_key, require_auth

router = APIRouter(tags=["auth"])


class _AuthRateLimiter:
    """S1.3: prosty rate-limit/lockout prób logowania (ochrona przed brute-force PIN)."""

    def __init__(self, max_attempts: int = 5, window_seconds: int = 300):
        self.max_attempts = max_attempts
        self.window = window_seconds
        self._attempts: Dict[str, Dict[str, float]] = {}

    @staticmethod
    def _now() -> float:
        import time

        return time.monotonic()

    def is_locked(self, key: str) -> bool:
        rec = self._attempts.get(key)
        if not rec:
            return False
        if self._now() - rec["first"] >= self.window:
            self._attempts.pop(key, None)
            return False
        return rec["count"] >= self.max_attempts

    def record_failure(self, key: str) -> None:
        now = self._now()
        rec = self._attempts.get(key)
        if not rec or now - rec["first"] >= self.window:
            self._attempts[key] = {"count": 1.0, "first": now}
        else:
            rec["count"] += 1

    def reset(self, key: str) -> None:
        self._attempts.pop(key, None)


_auth_limiter = _AuthRateLimiter()


@router.get("/api/status")
async def status():
    is_init = os.path.exists(vault.VAULT_DATA_FILE)
    return {"initialized": is_init}


@router.post("/api/init", response_model=schemas.SuccessResponse)
async def init_api(data: schemas.InitRequest):
    if os.path.exists(vault.VAULT_DATA_FILE):
        raise HTTPException(status_code=400, detail="Already initialized")

    try:
        vault.init_vault_core(data.pin, data.master)
        return schemas.SuccessResponse(success=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/auth", response_model=schemas.AuthResponse)
async def auth(data: schemas.AuthRequest, request: Request):
    client = request.client.host if request.client else "unknown"
    if _auth_limiter.is_locked(client):
        raise HTTPException(
            status_code=429,
            detail="Zbyt wiele nieudanych prób logowania. Spróbuj ponownie później.",
        )
    vk, role = get_auth_key(data.password)
    if vk:
        _auth_limiter.reset(client)
        return schemas.AuthResponse(success=True, role=role)
    _auth_limiter.record_failure(client)
    raise HTTPException(status_code=401, detail="Invalid credentials")


@router.post("/api/change-pin", response_model=schemas.SuccessResponse)
async def change_pin(
    req: schemas.ChangePinRequest,
    auth_data: Tuple[bytes, str, str] = Depends(require_auth),
):
    vk, role, _ = auth_data
    if role != "admin":
        raise HTTPException(status_code=403, detail="Admin role required to change PIN")

    try:
        vault.update_pin(vk, req.new_pin)
        return schemas.SuccessResponse(success=True, message="PIN zaktualizowany")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
