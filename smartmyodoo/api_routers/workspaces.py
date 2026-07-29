"""S3.1: domena `workspaces` (+ projekty/zadania/timesheet/task_bind) wydzielona z api.py.

Zachowanie bez zmian — pełne ścieżki `/api/workspaces/*` zachowane (router bez prefixu).
`require_auth` importowany z smartmyodoo.api (late). Helper `_get_odoo_connector` przeniesiony tu.
"""

import datetime
from typing import Optional, Tuple

from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from smartmyodoo.core.database import get_db
from smartmyodoo.core import models as db_models
from smartmyodoo.vault import vault
from smartmyodoo.vault import schemas
from smartmyodoo.vault.schemas import CredentialType
from smartmyodoo.vault.resolver import resolve_credential
from smartmyodoo.api_deps import require_auth

router = APIRouter(tags=["workspaces"])


@router.get("/api/workspaces")
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


def _resolve_odoo_creds(vault_data, ws_id, prefer_timesheet=False) -> dict:
    """K3: wybór poświadczeń Odoo po TYPIE.

    Dla logowania czasu pracy preferuj `odoo_timesheet` (osobne/rozliczeniowe Odoo),
    z fallbackiem na `odoo_data`. Dla reszty operacji — `odoo_data`.
    Na końcu fallback legacy po nazwie `{ws}_ODOO`/`default_ODOO` (kompatybilność).
    """
    cred = None
    if prefer_timesheet:
        cred = resolve_credential(vault_data, CredentialType.ODOO_TIMESHEET, ws_id)
    if cred is None:
        cred = resolve_credential(vault_data, CredentialType.ODOO_DATA, ws_id)
    if cred is not None:
        return {
            "url": cred.url,
            "db": cred.db,
            "login": cred.login,
            # AZURE-01 T1: klucz API Odoo działa jak hasło w authenticate/execute_kw
            # (Odoo 14+). Preferuj api_key nad password — spójnie z chat.py:56 — aby
            # sekret ODOO_DATA z samym kluczem (bez hasła) łączył też ścieżkę
            # workspace/timesheet. Connector czyta `api_key or password` w tym polu.
            "password": cred.api_key or cred.password or "",
            "default_project_ref": cred.default_project_ref,
            "default_task_ref": cred.default_task_ref,
        }
    # Legacy fallback (np. niekompletne stare sekrety, których resolver nie przyjął)
    secret_key = f"{ws_id}_ODOO"
    if secret_key not in vault_data:
        secret_key = "default_ODOO"  # nosec B105
    if secret_key not in vault_data:
        raise HTTPException(
            status_code=400, detail="Brak poświadczeń Odoo w sejfie dla tego workspace."
        )
    return vault_data[secret_key]


def _get_odoo_connector(vk, ws_id, prefer_timesheet=False):
    """Helper: pobiera OdooProjectConnector z poświadczeń Vault dla danego workspace."""
    vault_data = vault.load_vault(vk)
    creds = _resolve_odoo_creds(vault_data, ws_id, prefer_timesheet=prefer_timesheet)
    from smartmyodoo.core.odoo_connector import OdooProjectConnector

    return OdooProjectConnector(creds)


@router.get("/api/workspaces/{ws_id}/projects/search")
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
            kw={"fields": ["id", "name"], "limit": 30},
        )
        return projects
    except vault.VaultDecryptionError:
        raise HTTPException(status_code=500, detail="Błąd deszyfrowania sejfu")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/workspaces/{ws_id}/projects/{project_id}/tasks")
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
            kw={"fields": ["id", "name", "stage_id", "user_ids"], "limit": 200},
        )
        return tasks
    except vault.VaultDecryptionError:
        raise HTTPException(status_code=500, detail="Błąd deszyfrowania sejfu")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/workspaces/{ws_id}/tasks/search")
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
            kw={"fields": ["id", "name", "project_id"], "limit": 20},
        )
        return tasks
    except vault.VaultDecryptionError:
        raise HTTPException(status_code=500, detail="Błąd deszyfrowania sejfu")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class TimesheetRequest(BaseModel):
    hours: float
    description: str
    task_id: Optional[int] = None
    is_nominal: bool = False


@router.post("/api/workspaces/{ws_id}/timesheet")
async def log_timesheet(
    ws_id: str,
    payload: TimesheetRequest,
    auth_data: Tuple[bytes, str, str] = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Zapisuje wpis czasu pracy (timesheet) do Odoo."""
    ws = db.query(db_models.Workspace).filter(db_models.Workspace.id == ws_id).first()
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")

    vk, _, _ = auth_data
    try:
        # K3: logowanie czasu używa Odoo typu 'timesheet' (fallback na 'data')
        connector = _get_odoo_connector(vk, ws_id, prefer_timesheet=True)

        task_id = payload.task_id
        is_nominal = payload.is_nominal

        if not is_nominal and not task_id:
            task_id = int(ws.task_ref) if ws.task_ref else None

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

        project_id = ws.project_ref
        if not project_id:
            raise HTTPException(status_code=400, detail="Najpierw wybierz projekt.")

        entry_id = connector.log_timesheet(
            project_id=int(project_id),
            task_id=int(task_id),
            hours=payload.hours,
            description=payload.description,
        )
        return {"success": True, "timesheet_id": entry_id}
    except vault.VaultDecryptionError:
        raise HTTPException(status_code=500, detail="Błąd deszyfrowania sejfu")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class TaskBindRequest(BaseModel):
    project_ref: str
    project_name: str
    task_ref: str = ""
    task_name: str = ""


@router.put("/api/workspaces/{ws_id}/task_bind")
async def bind_workspace_task(
    ws_id: str,
    payload: TaskBindRequest,
    auth_data: Tuple[bytes, str, str] = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Zapisuje powiązanie projektu + domyślnego zadania."""
    ws = db.query(db_models.Workspace).filter(db_models.Workspace.id == ws_id).first()
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")

    ws.project_ref = payload.project_ref  # type: ignore
    ws.project_name = payload.project_name  # type: ignore
    ws.task_ref = payload.task_ref  # type: ignore
    ws.task_name = payload.task_name  # type: ignore
    db.commit()
    return {
        "success": True,
        "project_ref": ws.project_ref,
        "project_name": ws.project_name,
        "task_ref": ws.task_ref,
        "task_name": ws.task_name,
    }


@router.post("/api/workspaces")
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


@router.put("/api/workspaces/reorder")
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


@router.put("/api/workspaces/{ws_id}")
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


@router.delete("/api/workspaces/{ws_id}")
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
    secrets_reassigned = 0
    vk, _, _ = auth_data
    try:
        vault_data = vault.load_vault(vk)
        changed = False
        for key, val in list(vault_data.items()):
            if not (isinstance(val, dict) and val.get("workspace_id") == ws_id):
                continue
            if cascade_vault:
                # Tryb kaskady: soft-delete sekretów tej przestrzeni.
                vault_data[key]["deleted_at"] = datetime.datetime.now().isoformat()
                secrets_removed += 1
            elif ws_id != "default":
                # FIX (orphan-guard): „zachowaj sekrety" NIE może zostawiać wiszących
                # rekordów wskazujących na nieistniejącą przestrzeń — przepinamy je na
                # `default`, inaczej stają się niewidoczne (filtr widoku po workspace_id).
                vault_data[key]["workspace_id"] = "default"
                secrets_reassigned += 1
            changed = True
        if changed:
            vault.save_vault(vk, vault_data)
    except vault.VaultDecryptionError as e:
        import logging

        logging.warning(f"Vault re-parent/cascade failed for workspace {ws_id}: {e}")

    db.delete(ws)
    db.commit()
    return {
        "success": True,
        "secrets_removed": secrets_removed,
        "secrets_reassigned": secrets_reassigned,
    }
