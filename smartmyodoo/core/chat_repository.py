"""
Chat Repository — persystentna historia konwersacji.

Smart Context Pattern:
- Zapisuje KAŻDĄ wiadomość (user/assistant/tool) do SQLite.
- Przy wznowieniu sesji ładuje SKRÓTY (pierwsze 100 znaków + słowa kluczowe)
  zamiast pełnych wiadomości, oszczędzając tokeny LLM.
- Pełna konwersacja ładowana ON-DEMAND gdy temat bieżący dotyczy wcześniejszej sesji.
"""

import json
import logging
from typing import Optional

from sqlalchemy.orm import Session

from smartmyodoo.core.models import ChatMessage

logger = logging.getLogger(__name__)

# Max chars per message in summary mode (Smart Context)
SUMMARY_PREVIEW_LEN = 120


class ChatRepository:
    """Warstwa persystencji dla historii chatów."""

    def __init__(self, db: Session):
        self.db = db

    def save_message(
        self,
        workspace_id: str,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[dict] = None,
    ) -> ChatMessage:
        """Zapisz pojedynczą wiadomość do bazy."""
        msg = ChatMessage(
            workspace_id=workspace_id,
            session_id=session_id,
            role=role,
            content=content,
            metadata_json=json.dumps(metadata or {}, ensure_ascii=False),
        )
        self.db.add(msg)
        self.db.commit()
        self.db.refresh(msg)
        return msg

    def get_session_messages(self, session_id: str, limit: int = 200) -> list[dict]:
        """Pobierz PEŁNE wiadomości z danej sesji (on-demand load)."""
        rows = (
            self.db.query(ChatMessage)
            .filter(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.asc())
            .limit(limit)
            .all()
        )
        return [
            {
                "id": r.id,
                "role": r.role,
                "content": r.content,
                "metadata": json.loads(r.metadata_json) if r.metadata_json else {},  # type: ignore
                "created_at": r.created_at.isoformat() if r.created_at else "",
            }
            for r in rows
        ]

    def list_sessions(self, workspace_id: str, limit: int = 30) -> list[dict]:
        """
        Lista sesji per workspace — Smart Context.
        Zwraca skróty (preview) zamiast pełnych wiadomości.
        """
        from sqlalchemy import func as sa_func

        # Pobierz unikalne session_id z workspace
        session_ids = (
            self.db.query(ChatMessage.session_id)
            .filter(ChatMessage.workspace_id == workspace_id)
            .group_by(ChatMessage.session_id)
            .order_by(sa_func.max(ChatMessage.created_at).desc())
            .limit(limit)
            .all()
        )

        sessions = []
        for (sid,) in session_ids:
            # Pobierz pierwszą wiadomość user jako preview
            first_user_msg = (
                self.db.query(ChatMessage)
                .filter(
                    ChatMessage.session_id == sid,
                    ChatMessage.role == "user",
                )
                .order_by(ChatMessage.created_at.asc())
                .first()
            )
            preview = ""
            if first_user_msg and first_user_msg.content:
                preview = first_user_msg.content[:SUMMARY_PREVIEW_LEN]  # type: ignore
                if len(first_user_msg.content) > SUMMARY_PREVIEW_LEN:
                    preview += "..."

            # Policz wiadomości
            msg_count = (
                self.db.query(sa_func.count(ChatMessage.id))
                .filter(ChatMessage.session_id == sid)
                .scalar()
            )

            # Timestamp ostatniej wiadomości
            last_msg = (
                self.db.query(ChatMessage)
                .filter(ChatMessage.session_id == sid)
                .order_by(ChatMessage.created_at.desc())
                .first()
            )

            sessions.append(
                {
                    "session_id": sid,
                    "preview": preview,
                    "message_count": msg_count,
                    "last_activity": last_msg.created_at.isoformat()
                    if last_msg and last_msg.created_at
                    else "",
                }
            )

        return sessions

    def get_smart_context(
        self, workspace_id: str, current_session_id: str
    ) -> list[dict]:
        """
        Smart Context Pattern:
        Ładuje skróty z POPRZEDNICH sesji (nie bieżącej) jako kontekst dla LLM.
        Format: lista krótkich streszczeń ("W sesji X rozmawiano o Y").
        """
        sessions = self.list_sessions(workspace_id, limit=5)
        context_items = []
        for s in sessions:
            if s["session_id"] == current_session_id:
                continue  # Pomiń bieżącą sesję
            if s["preview"]:
                context_items.append(
                    {
                        "role": "system",
                        "content": f"[Poprzednia sesja ({s['session_id'][:8]}...): "
                        f'Użytkownik pytał: "{s["preview"]}" '
                        f"({s['message_count']} wiadomości)]",
                    }
                )
        return context_items

    def get_latest_session_id(self, workspace_id: str) -> Optional[str]:
        """Zwraca session_id ostatniej sesji w danym workspace."""
        row = (
            self.db.query(ChatMessage.session_id)
            .filter(ChatMessage.workspace_id == workspace_id)
            .order_by(ChatMessage.created_at.desc())
            .first()
        )
        return row[0] if row else None
