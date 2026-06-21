"""S3.1: read-only domena monitoringu (agent status, chat sessions, audit) wydzielona z api.py.

Zachowanie bez zmian — te same ścieżki i zależność `require_auth` (late import z smartmyodoo.api).
"""

from typing import Optional, Tuple

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from smartmyodoo.core.database import get_db
from smartmyodoo.core import models as db_models
from smartmyodoo.api_deps import require_auth

router = APIRouter(tags=["monitoring"])


@router.get("/api/version")
async def get_version():
    """RELEASE-01 T5 (US-REL-5): wersja wydania z metadanych pakietu (SSoT pyproject, D4).

    Publiczny (jak /api/status) — nie eksponuje danych wrażliwych, tylko numer wersji.
    """
    from smartmyodoo.core.runtime_info import get_app_version

    return {"version": get_app_version()}


@router.get("/api/agent/status")
async def get_agent_status(
    auth_data: Tuple[bytes, str, str] = Depends(require_auth),
):
    """Zwraca obecny status działania agenta (mock na potrzeby UI)."""
    return {"status": "idle", "task": None, "step": None, "elapsed_s": 0}


@router.get("/api/chat/sessions")
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


@router.get("/api/chat/sessions/{session_id}/messages")
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


@router.get("/api/audit")
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
