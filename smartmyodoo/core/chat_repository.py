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

    def get_recent_window(
        self, session_id: str, max_turns: int = 6, max_chars: int = 2000
    ) -> list[dict]:
        """TRUST-03 T1 (Buffer Window): ostatnie `max_turns` tur (user+assistant)
        bieżącej sesji — do ODTWORZENIA kontekstu w LLM (czego dziś brakuje).

        - Pomija rolę 'tool' (duże zrzuty Odoo; assistant je streszcza) → budżet.
        - Każdą treść przycina do `max_chars` (twardy limit na tokeny).
        - Zwraca chronologicznie [{role, content}] (najstarsze→najnowsze).
        Wynik to RAW historia (plaintext) — anonimizację robi warstwa wyżej.
        """
        if max_turns <= 0:
            return []
        msgs = self.get_session_messages(session_id, limit=400)
        convo = [m for m in msgs if m.get("role") in ("user", "assistant")]
        window = convo[-(2 * max_turns):]  # ≈ max_turns par user/assistant
        out: list[dict] = []
        for m in window:
            c = m.get("content") or ""
            if len(c) > max_chars:
                c = c[:max_chars] + " […]"
            out.append({"role": m["role"], "content": c})
        return out

    def _summarize_older(self, older: list[dict], budget: int = 4000) -> str:
        """TRUST-03 T3: deterministyczne (ekstraktywne) streszczenie starszych tur.

        Bez dodatkowego wywołania LLM (zero kosztu/latencji/ryzyka 'context poisoning').
        Zbiera wcześniejsze PYTANIA użytkownika (gist intencji) — identyfikatory rekordów
        i tak niesie kotwica Entity Memory (T2). Hook na summarizer LLM = przyszły upgrade.
        """
        user_qs = [
            (m.get("content") or "").strip()
            for m in older
            if m.get("role") == "user" and (m.get("content") or "").strip()
        ]
        if not user_qs:
            return ""
        digest = " | ".join(q[:120] for q in user_qs)[:budget]
        return (
            f"[STRESZCZENIE WCZEŚNIEJSZEJ ROZMOWY — {len(older)} wiadomości] "
            f"Wcześniejsze pytania użytkownika: {digest}"
        )

    def get_history_context(
        self,
        session_id: str,
        max_turns: int = 6,
        max_chars: int = 2000,
        summary_budget: int = 4000,
    ) -> list[dict]:
        """TRUST-03 T3 (Summary Buffer): ostatnie `max_turns` tur DOSŁOWNIE + (gdy są
        STARSZE tury poza oknem) JEDNO syntetyczne streszczenie na początku.

        Zwraca [ {role:'system', synthetic:True}?, <okno user/assistant...> ] (RAW —
        anonimizację robi warstwa wyżej). To produkcyjny wzorzec rynku (last-N + summary).
        """
        if max_turns <= 0:
            return []
        msgs = self.get_session_messages(session_id, limit=600)
        convo = [m for m in msgs if m.get("role") in ("user", "assistant")]
        if not convo:
            return []
        win_size = 2 * max_turns
        window = convo[-win_size:]
        older = convo[:-win_size] if len(convo) > win_size else []

        out: list[dict] = []
        if older:  # rozmowa dłuższa niż okno → streść starsze tury
            summary = self._summarize_older(older, summary_budget)
            if summary:
                out.append({"role": "system", "content": summary, "synthetic": True})
        for m in window:
            c = m.get("content") or ""
            if len(c) > max_chars:
                c = c[:max_chars] + " […]"
            out.append({"role": m["role"], "content": c})
        return out

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
