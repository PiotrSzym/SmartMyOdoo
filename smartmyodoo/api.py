import os
import datetime
import json
from typing import Dict, Any, Tuple, Optional
from fastapi import FastAPI, Depends, HTTPException, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from smartmyodoo.core.database import get_db, engine
from smartmyodoo.core import models as db_models

from smartmyodoo.vault import vault
from smartmyodoo.vault import schemas
from smartmyodoo.swarm.models import (
    ChatRequest,
    ChatResponse,
)
from smartmyodoo.swarm.dispatcher import Dispatcher
from smartmyodoo.swarm import llm_client

db_models.Base.metadata.create_all(bind=engine)

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

# Zastąpiono _proposals i _workspaces użyciem bazy danych.


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
            "db": secret_data.db,
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
    db: Session = Depends(get_db),
):
    result = dispatcher.classify_intent(req.message)

    PERSONA_REPLIES = {
        "A": "[💻 Developer] Rozumiem — chcesz napisać lub poprawić kod. Przygotowuję rozwiązanie...",
        "B": "[🗄️ DBA] Przyjęto zapytanie. Analizuję polecenie i przygotowuję akcję na bazie Odoo...",
        "C": "[🧪 QA] Przygotowuję testy i walidację dla Twojego żądania...",
        "D": "[📝 Docs] Generuję dokumentację na podstawie Twojego opisu...",
        "E": "[🔍 Scout] Rozpoczynam research — przeszukuję bazę wiedzy...",
        "F": "[🏗️ Architect] Analizuję architekturę systemu pod kątem Twojego pytania...",
        "G": "[📊 PM] Aktualizuję status projektu i organizuję zadania...",
        "H": "[🤖 Asystent] {message_echo}",
    }

    reply_template = PERSONA_REPLIES.get(result.category.value, PERSONA_REPLIES["H"])
    reply_text = reply_template.format(message_echo=req.message)

    return ChatResponse(
        reply=reply_text,
        action_type="CHAT",
        category=result.category.value,
        persona=result.persona.value if result.persona else "H",
        model=result.recommended_model,
    )


# ── EP-Agent: Agent Status API ───────────────────────────────────────────────


@app.get("/api/agent/status")
async def get_agent_status(
    auth_data: Tuple[bytes, str, str] = Depends(require_auth),
):
    """Zwraca obecny status działania agenta (mock na potrzeby UI)."""
    return {"status": "idle", "task": None, "step": None, "elapsed_s": 0}


# ── EP-1: Chat Sessions API ──────────────────────────────────────────────────


@app.get("/api/chat/sessions")
async def get_chat_sessions(
    workspace_id: str = "default",
    limit: int = 20,
    auth_data: Tuple[bytes, str, str] = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Lista sesji czatu dla danego workspace (Smart Context)."""
    from smartmyodoo.core.chat_repository import ChatRepository

    repo = ChatRepository(db=db)
    return repo.list_sessions(workspace_id, limit=limit)


@app.get("/api/chat/sessions/{session_id}/messages")
async def get_session_messages(
    session_id: str,
    limit: int = 200,
    auth_data: Tuple[bytes, str, str] = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Pełna historia wiadomości z konkretnej sesji (on-demand load)."""
    from smartmyodoo.core.chat_repository import ChatRepository

    repo = ChatRepository(db=db)
    return repo.get_session_messages(session_id, limit=limit)


# ── EP-3: Audit Trail API ────────────────────────────────────────────────────


@app.get("/api/audit")
async def get_audit_log(
    workspace_id: Optional[str] = None,
    limit: int = 50,
    auth_data: Tuple[bytes, str, str] = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Pobierz ostatnie wpisy z dziennika audytu."""
    query = db.query(db_models.AuditLog).order_by(db_models.AuditLog.timestamp.desc())
    if workspace_id:
        query = query.filter(db_models.AuditLog.workspace_id == workspace_id)
    entries = query.limit(limit).all()
    return [
        {
            "id": e.id,
            "workspace_id": e.workspace_id,
            "timestamp": e.timestamp.isoformat() if e.timestamp else "",
            "action": e.action,
            "details": e.details,
        }
        for e in entries
    ]


# ── HUB-S3: Proposals API ────────────────────────────────────────────────────


@app.get("/api/proposals")
async def get_proposals(
    workspace_id: Optional[str] = None,
    auth_data: Tuple[bytes, str, str] = Depends(require_auth),
    db: Session = Depends(get_db),
):
    query = db.query(db_models.Proposal)
    if workspace_id:
        query = query.filter(db_models.Proposal.workspace_id == workspace_id)
    proposals = query.all()

    res = []
    for p in proposals:
        res.append(
            {
                "id": p.id,
                "workspace_id": p.workspace_id,
                "odoo_model": p.odoo_model,
                "method": p.method,
                "values": json.loads(str(p.values)) if p.values else {},
                "reason": p.reason,
                "status": p.status,
                "created_at": p.created_at.isoformat() if p.created_at else "",
            }
        )
    return res


@app.post("/api/proposals/{proposal_id}/approve")
async def approve_proposal(
    proposal_id: str,
    auth_data: Tuple[bytes, str, str] = Depends(require_auth),
    db: Session = Depends(get_db),
):
    prop = (
        db.query(db_models.Proposal)
        .filter(db_models.Proposal.id == proposal_id)
        .first()
    )
    if not prop:
        raise HTTPException(status_code=404, detail="Proposal not found")
    prop.status = "approved"  # type: ignore
    db.commit()
    return {"success": True, "status": "approved"}


@app.post("/api/proposals/{proposal_id}/reject")
async def reject_proposal(
    proposal_id: str,
    auth_data: Tuple[bytes, str, str] = Depends(require_auth),
    db: Session = Depends(get_db),
):
    prop = (
        db.query(db_models.Proposal)
        .filter(db_models.Proposal.id == proposal_id)
        .first()
    )
    if not prop:
        raise HTTPException(status_code=404, detail="Proposal not found")
    prop.status = "rejected"  # type: ignore
    db.commit()
    return {"success": True, "status": "rejected"}


# ── HUB-S3: Workspaces API ──────────────────────────────────────────────────────────────


@app.get("/api/workspaces")
async def get_workspaces(
    auth_data: Tuple[bytes, str, str] = Depends(require_auth),
    db: Session = Depends(get_db),
):
    wks = db.query(db_models.Workspace).order_by(db_models.Workspace.position).all()
    if not wks:
        # Defaults if empty
        default_wks = [
            db_models.Workspace(id="default", name="Domyślna", position=0),
            db_models.Workspace(id="dev", name="Dev Env", position=1),
            db_models.Workspace(id="prod", name="Production", position=2),
        ]
        db.add_all(default_wks)
        db.commit()
        wks = db.query(db_models.Workspace).order_by(db_models.Workspace.position).all()

    return [
        {
            "id": w.id,
            "name": w.name,
            "odoo_url": w.odoo_url,
            "position": w.position,
            "project_ref": w.project_ref,
            "project_name": w.project_name,
            "task_ref": w.task_ref,
            "task_name": w.task_name,
        }
        for w in wks
    ]


# ── EP-5.4: Project + Task Binding API ───────────────────────────────────────


def _get_odoo_connector(vk, ws_id):
    """Helper: pobiera OdooProjectConnector z poświadczeń Vault dla danego workspace."""
    vault_data = vault.load_vault(vk)
    secret_key = f"{ws_id}_ODOO"
    if secret_key not in vault_data:
        secret_key = "default_ODOO"  # nosec B105
    if secret_key not in vault_data:
        raise HTTPException(
            status_code=400, detail="Brak poświadczeń Odoo w sejfie dla tego workspace."
        )
    creds = vault_data[secret_key]
    from smartmyodoo.core.odoo_connector import OdooProjectConnector

    return OdooProjectConnector(creds)


@app.get("/api/workspaces/{ws_id}/projects/search")
async def search_odoo_projects(
    ws_id: str,
    query: str = "",
    auth_data: Tuple[bytes, str, str] = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Szuka projektów w Odoo (project.project)."""
    vk, _, _ = auth_data
    try:
        connector = _get_odoo_connector(vk, ws_id)
        domain = [("name", "ilike", query)] if query else []
        projects = connector.execute_kw(
            model="project.project",
            method="search_read",
            args=[domain],
            kwargs={"fields": ["id", "name"], "limit": 30},
        )
        return projects
    except vault.VaultDecryptionError:
        raise HTTPException(status_code=500, detail="Błąd deszyfrowania sejfu")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/workspaces/{ws_id}/projects/{project_id}/tasks")
async def list_project_tasks(
    ws_id: str,
    project_id: int,
    auth_data: Tuple[bytes, str, str] = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Zwraca wszystkie zadania z danego projektu Odoo."""
    vk, _, _ = auth_data
    try:
        connector = _get_odoo_connector(vk, ws_id)
        domain = [("project_id", "=", project_id)]
        tasks = connector.execute_kw(
            model="project.task",
            method="search_read",
            args=[domain],
            kwargs={"fields": ["id", "name", "stage_id", "user_ids"], "limit": 200},
        )
        return tasks
    except vault.VaultDecryptionError:
        raise HTTPException(status_code=500, detail="Błąd deszyfrowania sejfu")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/workspaces/{ws_id}/tasks/search")
async def search_odoo_tasks(
    ws_id: str,
    query: str = "",
    auth_data: Tuple[bytes, str, str] = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Szuka zadań w Odoo (project.task) — zachowane dla kompatybilności."""
    vk, _, _ = auth_data
    try:
        connector = _get_odoo_connector(vk, ws_id)
        domain = [("name", "ilike", query)] if query else []
        tasks = connector.execute_kw(
            model="project.task",
            method="search_read",
            args=[domain],
            kwargs={"fields": ["id", "name", "project_id"], "limit": 20},
        )
        return tasks
    except vault.VaultDecryptionError:
        raise HTTPException(status_code=500, detail="Błąd deszyfrowania sejfu")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/workspaces/{ws_id}/task_bind")
async def bind_workspace_task(
    ws_id: str,
    payload: dict,
    auth_data: Tuple[bytes, str, str] = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Zapisuje powiązanie projektu + domyślnego zadania."""
    ws = db.query(db_models.Workspace).filter(db_models.Workspace.id == ws_id).first()
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")

    ws.project_ref = payload.get("project_ref", "")
    ws.project_name = payload.get("project_name", "")
    ws.task_ref = payload.get("task_ref", "")
    ws.task_name = payload.get("task_name", "")
    db.commit()
    return {
        "success": True,
        "project_ref": ws.project_ref,
        "project_name": ws.project_name,
        "task_ref": ws.task_ref,
        "task_name": ws.task_name,
    }


@app.post("/api/workspaces/{ws_id}/log_time")
async def log_workspace_time(
    ws_id: str,
    payload: dict,
    auth_data: Tuple[bytes, str, str] = Depends(require_auth),
    db: Session = Depends(get_db),
):
    ws = db.query(db_models.Workspace).filter(db_models.Workspace.id == ws_id).first()
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")

    vk, _, _ = auth_data
    try:
        vault_data = vault.load_vault(vk)
        secret_key = f"{ws_id}_ODOO"
        if secret_key not in vault_data:
            raise HTTPException(
                status_code=400, detail="Brak poświadczeń Odoo w sejfie"
            )

        # Jeśli wymuszamy auto-logowanie, a brak task_ref, stwórzmy domyślne zadanie
        connector = _get_odoo_connector(vk, ws_id)

        task_id = payload.get("task_id")
        is_nominal = payload.get("is_nominal", False)

        # Jeśli nie nominalny, to automatyczny - idzie na domyślny task z workspace
        if not is_nominal and not task_id:
            task_id = ws.task_ref

            # Auto-create if not present
            if not task_id and ws.project_ref:
                try:
                    task_id = connector.create_task(
                        int(ws.project_ref), "[SmartMyOdoo] Pula czasu roboczego"
                    )
                    ws.task_ref = str(task_id)  # type: ignore
                    ws.task_name = "[SmartMyOdoo] Pula czasu roboczego"  # type: ignore
                    db.commit()
                except Exception as e:
                    raise HTTPException(
                        status_code=500, detail=f"Błąd auto-create task: {str(e)}"
                    )

        if not task_id:
            raise HTTPException(
                status_code=400, detail="Brak ID zadania (task_id) dla logowania czasu."
            )

        project_id = payload.get("project_id") or ws.project_ref
        res = connector.log_timesheet(
            project_id=int(project_id) if project_id else False,
            task_id=int(task_id),
            hours=payload.get("hours", 0.0),
            description=payload.get("description", "Praca agenta AI"),
        )
        return {"success": True, "timesheet_id": res}
    except vault.VaultDecryptionError:
        raise HTTPException(status_code=500, detail="Błąd deszyfrowania sejfu")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/workspaces")
async def create_workspace(
    ws: schemas.WorkspaceCreateRequest,
    auth_data: Tuple[bytes, str, str] = Depends(require_auth),
    db: Session = Depends(get_db),
):
    existing = (
        db.query(db_models.Workspace).filter(db_models.Workspace.id == ws.id).first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="Workspace ID already exists")
    max_pos = db.query(db_models.Workspace).count()
    new_ws = db_models.Workspace(
        id=ws.id, name=ws.name, odoo_url=ws.odoo_url, position=max_pos
    )
    db.add(new_ws)
    db.commit()

    vault_saved = False
    if ws.admin_password:
        vk, _, _ = auth_data
        try:
            vault_data = vault.load_vault(vk)
            secret_key = f"{ws.id}_ODOO"
            vault_data[secret_key] = {
                "password": ws.admin_password,
                "login": ws.admin_login or "",
                "api_key": ws.admin_api_key or "",
                "url": ws.odoo_url or "",
                "workspace_id": ws.id,
                "expires": ws.admin_expires or "",
            }
            vault.save_vault(vk, vault_data)
            vault_saved = True
        except vault.VaultDecryptionError as e:
            import logging

            logging.warning(f"Vault write failed for workspace {ws.id}: {e}")

    return {"success": True, "id": ws.id, "vault_saved": vault_saved}


@app.put("/api/workspaces/reorder")
async def reorder_workspaces(
    body: dict,
    auth_data: Tuple[bytes, str, str] = Depends(require_auth),
    db: Session = Depends(get_db),
):
    order = body.get("order", [])
    if not order:
        raise HTTPException(status_code=400, detail="Empty order list")

    for idx, ws_id in enumerate(order):
        ws = (
            db.query(db_models.Workspace)
            .filter(db_models.Workspace.id == ws_id)
            .first()
        )
        if ws:
            ws.position = idx  # type: ignore
    db.commit()
    return {"success": True}


@app.put("/api/workspaces/{ws_id}")
async def update_workspace(
    ws_id: str,
    update_data: dict,
    auth_data: Tuple[bytes, str, str] = Depends(require_auth),
    db: Session = Depends(get_db),
):
    ws = db.query(db_models.Workspace).filter(db_models.Workspace.id == ws_id).first()
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")

    ws.name = update_data.get("name", ws.name)
    ws.odoo_url = update_data.get("odoo_url", ws.odoo_url)
    db.commit()
    return {"success": True}


@app.delete("/api/workspaces/{ws_id}")
async def delete_workspace(
    ws_id: str,
    cascade_vault: bool = False,
    auth_data: Tuple[bytes, str, str] = Depends(require_auth),
    db: Session = Depends(get_db),
):
    ws = db.query(db_models.Workspace).filter(db_models.Workspace.id == ws_id).first()
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")

    secrets_removed = 0
    if cascade_vault:
        vk, _, _ = auth_data
        try:
            vault_data = vault.load_vault(vk)
            for key, val in list(vault_data.items()):
                if isinstance(val, dict) and val.get("workspace_id") == ws_id:
                    vault_data[key]["deleted_at"] = datetime.datetime.now().isoformat()
                    secrets_removed += 1
            if secrets_removed > 0:
                vault.save_vault(vk, vault_data)
        except vault.VaultDecryptionError as e:
            import logging

            logging.warning(f"Vault cascade failed for workspace {ws_id}: {e}")

    db.delete(ws)
    db.commit()
    return {"success": True, "secrets_removed": secrets_removed}


@app.delete("/api/secrets/by-workspace/{ws_id}")
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
