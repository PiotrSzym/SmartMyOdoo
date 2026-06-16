"""FIX-02 S3.1: domena `secrets` wydzielona z api.py (God Module).

Zachowanie bez zmian — pełne ścieżki `/api/secrets/*` zachowane (router bez prefixu).
`require_auth` z api_deps (S3.4 — brak cyklu importów).
"""

import datetime
from typing import Any, Dict, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException

from smartmyodoo.vault import vault
from smartmyodoo.vault import schemas
from smartmyodoo.api_deps import require_auth

router = APIRouter(tags=["secrets"])


@router.get("/api/secrets", response_model=Dict[str, Any])
async def get_secrets(
    workspace_id: Optional[str] = None,
    auth_data: Tuple[bytes, str, str] = Depends(require_auth),
):
    vk, _, _ = auth_data
    try:
        data = vault.get_secrets(vk)
        if workspace_id:
            filtered_data = {
                k: v
                for k, v in data.items()
                if isinstance(v, dict)
                and v.get("workspace_id", "default") == workspace_id
            }
            return filtered_data
        return data
    except vault.VaultDecryptionError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/secrets/{key_name}", response_model=schemas.SuccessResponse)
async def add_or_update_secret(
    key_name: str,
    secret_data: schemas.SecretCreateRequest,
    auth_data: Tuple[bytes, str, str] = Depends(require_auth),
):
    vk, _, _ = auth_data
    try:
        data = vault.load_vault(vk)
        data[key_name] = {
            "password": secret_data.password,
            "login": secret_data.login,
            "url": secret_data.url,
            "db": secret_data.db,
            "api_key": secret_data.api_key,
            "expires": secret_data.expires,
            "workspace_id": secret_data.workspace_id,
            # K6 (KEY-01): typowany rejestr — zapisujemy typ/provider/ref timesheet
            "type": secret_data.type,
            "provider": secret_data.provider,
            "default_project_ref": secret_data.default_project_ref,
            "default_task_ref": secret_data.default_task_ref,
        }
        vault.save_vault(vk, data)
        return schemas.SuccessResponse(success=True)
    except vault.VaultDecryptionError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/api/secrets/{key_name}", response_model=schemas.SuccessResponse)
async def delete_secret(
    key_name: str, auth_data: Tuple[bytes, str, str] = Depends(require_auth)
):
    vk, _, _ = auth_data
    try:
        data = vault.load_vault(vk)
        if key_name in data:
            data[key_name]["deleted_at"] = datetime.datetime.now().isoformat()
            vault.save_vault(vk, data)
            return schemas.SuccessResponse(success=True)
        raise HTTPException(status_code=404, detail="Not found")
    except vault.VaultDecryptionError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/secrets/{key_name}/restore", response_model=schemas.SuccessResponse)
async def restore_secret(
    key_name: str, auth_data: Tuple[bytes, str, str] = Depends(require_auth)
):
    vk, _, _ = auth_data
    try:
        data = vault.load_vault(vk)
        if (
            key_name in data
            and isinstance(data[key_name], dict)
            and "deleted_at" in data[key_name]
        ):
            del data[key_name]["deleted_at"]
            vault.save_vault(vk, data)
            return schemas.SuccessResponse(success=True)
        raise HTTPException(status_code=404, detail="Not found or not deleted")
    except vault.VaultDecryptionError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete(
    "/api/secrets/{key_name}/permanent", response_model=schemas.SuccessResponse
)
async def permanent_delete_secret(
    key_name: str, auth_data: Tuple[bytes, str, str] = Depends(require_auth)
):
    vk, _, _ = auth_data
    try:
        data = vault.load_vault(vk)
        if key_name in data:
            del data[key_name]
            vault.save_vault(vk, data)
            return schemas.SuccessResponse(success=True)
        raise HTTPException(status_code=404, detail="Not found")
    except vault.VaultDecryptionError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/api/secrets/by-workspace/{ws_id}")
async def delete_secrets_by_workspace(
    ws_id: str,
    auth_data: Tuple[bytes, str, str] = Depends(require_auth),
):
    vk, _, _ = auth_data
    try:
        vault_data = vault.load_vault(vk)
        removed = 0
        for key, val in list(vault_data.items()):
            if isinstance(val, dict) and val.get("workspace_id") == ws_id:
                vault_data[key]["deleted_at"] = datetime.datetime.now().isoformat()
                removed += 1
        if removed > 0:
            vault.save_vault(vk, vault_data)
        return {"success": True, "secrets_removed": removed}
    except vault.VaultDecryptionError as e:
        raise HTTPException(status_code=500, detail=str(e))
