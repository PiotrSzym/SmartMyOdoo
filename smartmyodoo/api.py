import os
import datetime
from typing import Dict, Any, Tuple, Optional
from fastapi import FastAPI, Depends, HTTPException, Request, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse

from smartmyodoo.vault import vault
from smartmyodoo.vault import schemas

app = FastAPI(title="SmartMyVault API", description="FastAPI migration of Vault API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()

def get_auth_key(pwd: str) -> Tuple[Optional[bytes], Optional[str]]:
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

def require_auth(credentials: HTTPAuthorizationCredentials = Security(security)) -> Tuple[bytes, str, str]:
    pwd = credentials.credentials
    vk, role = get_auth_key(pwd)
    if not vk:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return vk, role, pwd

@app.get("/api/status")
async def status():
    is_init = os.path.exists(vault.VAULT_DATA_FILE)
    return {"initialized": is_init}

@app.post("/api/init", response_model=schemas.SuccessResponse)
async def init_api(data: schemas.InitRequest):
    if os.path.exists(vault.VAULT_DATA_FILE):
        raise HTTPException(status_code=400, detail="Already initialized")
    
    try:
        vault.init_vault_core(data.pin, data.master)
        return schemas.SuccessResponse(success=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/auth", response_model=schemas.AuthResponse)
async def auth(data: schemas.AuthRequest):
    vk, role = get_auth_key(data.password)
    if vk:
        return schemas.AuthResponse(success=True, role=role)
    raise HTTPException(status_code=401, detail="Invalid credentials")

@app.get("/api/secrets", response_model=Dict[str, Any])
async def get_secrets(auth_data: Tuple[bytes, str, str] = Depends(require_auth)):
    vk, _, _ = auth_data
    try:
        data = vault.get_secrets(vk)
        return data
    except vault.VaultDecryptionError as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/secrets/{key_name}", response_model=schemas.SuccessResponse)
async def add_or_update_secret(key_name: str, secret_data: schemas.SecretCreateRequest, auth_data: Tuple[bytes, str, str] = Depends(require_auth)):
    vk, _, _ = auth_data
    try:
        data = vault.load_vault(vk)
        data[key_name] = {
            "password": secret_data.password,
            "login": secret_data.login,
            "url": secret_data.url,
            "api_key": secret_data.api_key,
            "expires": secret_data.expires
        }
        vault.save_vault(vk, data)
        return schemas.SuccessResponse(success=True)
    except vault.VaultDecryptionError as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/secrets/{key_name}", response_model=schemas.SuccessResponse)
async def delete_secret(key_name: str, auth_data: Tuple[bytes, str, str] = Depends(require_auth)):
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

@app.post("/api/secrets/{key_name}/restore", response_model=schemas.SuccessResponse)
async def restore_secret(key_name: str, auth_data: Tuple[bytes, str, str] = Depends(require_auth)):
    vk, _, _ = auth_data
    try:
        data = vault.load_vault(vk)
        if key_name in data and isinstance(data[key_name], dict) and "deleted_at" in data[key_name]:
            del data[key_name]["deleted_at"]
            vault.save_vault(vk, data)
            return schemas.SuccessResponse(success=True)
        raise HTTPException(status_code=404, detail="Not found or not deleted")
    except vault.VaultDecryptionError as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/secrets/{key_name}/permanent", response_model=schemas.SuccessResponse)
async def permanent_delete_secret(key_name: str, auth_data: Tuple[bytes, str, str] = Depends(require_auth)):
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

@app.post("/api/change-pin", response_model=schemas.SuccessResponse)
async def change_pin(req: schemas.ChangePinRequest, auth_data: Tuple[bytes, str, str] = Depends(require_auth)):
    vk, role, _ = auth_data
    if role != "admin":
        raise HTTPException(status_code=403, detail="Admin role required to change PIN")
    
    try:
        vault.update_pin(vk, req.new_pin)
        return schemas.SuccessResponse(success=True, message="PIN zaktualizowany")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def start_server(port=8000):
    import uvicorn
    import webbrowser
    import threading
    import time
    
    url = f"http://127.0.0.1:{port}"
    print(f"==================================================")
    print(f"|  FastAPI Vault Server działa: {url} |")
    print(f"|  Proszę nie zamykać tej konsoli.               |")
    print(f"==================================================")
    
    def open_browser():
        time.sleep(1)
        webbrowser.open(url + "/docs")
    threading.Thread(target=open_browser, daemon=True).start()
    
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")

if __name__ == "__main__":
    start_server()
