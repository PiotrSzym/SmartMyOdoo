import os
import datetime
import uuid
from typing import Dict, Any, List, Tuple, Optional
from fastapi import FastAPI, Depends, HTTPException, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles

from smartmyodoo.vault import vault
from smartmyodoo.vault import schemas
from smartmyodoo.swarm.models import (
    ChatRequest,
    ChatResponse,
    ChatProposalData,
    Proposal,
    WorkspaceInfo,
    IntentCategory,
)
from smartmyodoo.swarm.dispatcher import Dispatcher
from smartmyodoo.swarm import llm_client

app = FastAPI(title="SmartMyVault API", description="FastAPI migration of Vault API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()

# LLM Client: odczyt klucza z ENV (opcjonalnie wstrzyknięty przez Vault CLI)
_llm = llm_client.create_client(api_key=os.environ.get("OPENROUTER_KEY"))
dispatcher = Dispatcher(llm_client=_llm)

# In-memory stores (HUB-S3)
_proposals: Dict[str, Proposal] = {}
_workspaces: List[WorkspaceInfo] = [
    WorkspaceInfo(id="default", name="Domyślna"),
    WorkspaceInfo(id="dev", name="Dev Env"),
    WorkspaceInfo(id="prod", name="Production"),
]


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


def require_auth(
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> Tuple[bytes, str, str]:
    pwd = credentials.credentials
    vk, role = get_auth_key(pwd)
    if not vk:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return vk, str(role), pwd


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


@app.post("/api/secrets/{key_name}", response_model=schemas.SuccessResponse)
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
            "api_key": secret_data.api_key,
            "expires": secret_data.expires,
            "workspace_id": secret_data.workspace_id,
        }
        vault.save_vault(vk, data)
        return schemas.SuccessResponse(success=True)
    except vault.VaultDecryptionError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/secrets/{key_name}", response_model=schemas.SuccessResponse)
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


@app.post("/api/secrets/{key_name}/restore", response_model=schemas.SuccessResponse)
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


@app.delete("/api/secrets/{key_name}/permanent", response_model=schemas.SuccessResponse)
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


@app.post("/api/change-pin", response_model=schemas.SuccessResponse)
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


@app.post("/api/chat", response_model=ChatResponse)
async def handle_chat(
    req: ChatRequest,
    auth_data: Tuple[bytes, str, str] = Depends(require_auth),
):
    result = dispatcher.classify_intent(req.message)

    # Shadow Mode: kategoria B (DBA) → automatyczna propozycja
    if result.category == IntentCategory.B_DATABASE_ADMIN:
        proposal_id = str(uuid.uuid4())[:8]
        proposal = Proposal(
            id=proposal_id,
            workspace_id=req.workspace_id,
            odoo_model="res.partner",
            method="CREATE",
            values={"name": "Z wiadomości: " + req.message[:50]},
            reason=f"Dispatcher wykrył intencję bazodanową: {req.message[:80]}",
            status="pending",
            created_at=datetime.datetime.now().isoformat(),
        )
        _proposals[proposal_id] = proposal

        return ChatResponse(
            reply="[🗄️ DBA] Wygenerowano propozycję Shadow Mode dla operacji na bazie danych.",
            action_type="SHADOW_PROPOSAL",
            category=result.category.value,
            persona=result.persona.value,
            model=result.recommended_model,
            proposal_data=ChatProposalData(
                proposal_id=proposal_id,
                text=proposal.reason,
                model=proposal.odoo_model,
                method=proposal.method,
                args=list(proposal.values.values()),
            ),
        )

    reply_text = f"[{result.persona.value}] Zklasyfikowano jako kategoria {result.category.value}. Wiadomość: {req.message}"
    return ChatResponse(
        reply=reply_text,
        action_type="CHAT",
        category=result.category.value,
        persona=result.persona.value,
        model=result.recommended_model,
    )


# ── HUB-S3: Proposals API ────────────────────────────────────────────────────


@app.get("/api/proposals")
async def get_proposals(
    workspace_id: Optional[str] = None,
    auth_data: Tuple[bytes, str, str] = Depends(require_auth),
):
    proposals = list(_proposals.values())
    if workspace_id:
        proposals = [p for p in proposals if p.workspace_id == workspace_id]
    return [p.model_dump() for p in proposals]


@app.post("/api/proposals/{proposal_id}/approve")
async def approve_proposal(
    proposal_id: str,
    auth_data: Tuple[bytes, str, str] = Depends(require_auth),
):
    if proposal_id not in _proposals:
        raise HTTPException(status_code=404, detail="Proposal not found")
    _proposals[proposal_id].status = "approved"
    return {"success": True, "status": "approved"}


@app.post("/api/proposals/{proposal_id}/reject")
async def reject_proposal(
    proposal_id: str,
    auth_data: Tuple[bytes, str, str] = Depends(require_auth),
):
    if proposal_id not in _proposals:
        raise HTTPException(status_code=404, detail="Proposal not found")
    _proposals[proposal_id].status = "rejected"
    return {"success": True, "status": "rejected"}


# ── HUB-S3: Workspaces API ──────────────────────────────────────────────────────────────


@app.get("/api/workspaces")
async def get_workspaces(
    auth_data: Tuple[bytes, str, str] = Depends(require_auth),
):
    return [w.model_dump() for w in _workspaces]


@app.post("/api/workspaces")
async def create_workspace(
    ws: WorkspaceInfo,
    auth_data: Tuple[bytes, str, str] = Depends(require_auth),
):
    # Sprawdź duplikaty
    if any(w.id == ws.id for w in _workspaces):
        raise HTTPException(status_code=400, detail="Workspace ID already exists")
    _workspaces.append(ws)
    return {"success": True, "id": ws.id}


ui_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ui")
app.mount("/", StaticFiles(directory=ui_dir, html=True), name="ui")


def start_server(port=8000):
    import uvicorn
    import webbrowser
    import threading
    import time

    url = f"http://127.0.0.1:{port}"
    print("==================================================")
    print(f"|  FastAPI Vault Server działa: {url} |")
    print("|  Proszę nie zamykać tej konsoli.               |")
    print("==================================================")

    def open_browser():
        time.sleep(1)
        webbrowser.open(url + "/")

    threading.Thread(target=open_browser, daemon=True).start()

    uvicorn.run("smartmyodoo.api:app", host="127.0.0.1", port=port, log_level="info")


if __name__ == "__main__":
    start_server()
