"""MEM-01: lekka pamięć historii (SQLite FTS5) — przypominanie rozmów i rozwiązanych
problemów BEZ wektorowego RAG.

Po co: użytkownik chce, by asystent pamiętał historię chatów i rozwiązane problemy
(sprinty). Wektorowy RAG (LanceDB + sentence-transformers + torch) jest dla tego
overkill i NIE działa pewnie na Py3.14 (brak wheeli torcha). FTS5 jest wbudowane w
sqlite Pythona → ZERO nowych zależności, działa lokalnie OD RĘKI i u każdego, kto
sklonuje repo. Indeks budujemy z: historii chatów (chat_messages) + sprintów
(docs/sprints) + knowledge/. Dane są małe (setki rekordów) → reindex jest tani.
"""

from __future__ import annotations

import glob
import os
import re
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

_FTS = "memory_fts"
_WORD_RE = re.compile(r"\w{2,}", re.UNICODE)


def _db_file() -> str:
    """Ścieżka pliku SQLite z DATABASE_URL (obsługa sqlite:/// i sqlite:////absolute)."""
    url = os.environ.get("DATABASE_URL", "sqlite:///smartmyodoo.db").strip()
    return url.replace("sqlite:///", "") if url.startswith("sqlite") else "smartmyodoo.db"


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def _connect(db_path: Optional[str] = None) -> sqlite3.Connection:
    con = sqlite3.connect(db_path or _db_file())
    con.row_factory = sqlite3.Row
    return con


def ensure_index(con: sqlite3.Connection) -> None:
    con.execute(
        f"CREATE VIRTUAL TABLE IF NOT EXISTS {_FTS} USING fts5("
        "source, ref, title, content, tokenize='unicode61')"
    )


def _fts_query(query: str) -> str:
    """Zbuduj BEZPIECZNE zapytanie FTS5 z tekstu usera: tokeny (≥2 znaki) jako fraza,
    łączone OR (lepszy recall). Eliminuje znaki specjalne FTS (', \", *, :) → brak
    błędów składni i wstrzyknięć."""
    tokens = _WORD_RE.findall(query or "")
    return " OR ".join(f'"{t}"' for t in tokens)


def reindex(con: sqlite3.Connection, *, workspace_id: Optional[str] = None) -> int:
    """Przebuduj indeks z chatów + sprintów + knowledge. Zwraca liczbę zaindeksowanych
    rekordów. Tani (małe dane) → wołany przy każdym wyszukaniu dla świeżości."""
    ensure_index(con)
    con.execute(f"DELETE FROM {_FTS}")
    n = 0

    # 1. Historia chatów (rozmowy)
    try:
        q = "SELECT session_id, role, content, created_at FROM chat_messages"
        params: tuple = ()
        if workspace_id:
            q += " WHERE workspace_id=?"
            params = (workspace_id,)
        for r in con.execute(q, params):
            content = (r["content"] or "").strip()
            if not content:
                continue
            con.execute(
                f"INSERT INTO {_FTS}(source,ref,title,content) VALUES('chat',?,?,?)",
                (r["session_id"], f"{r['role']} @ {r['created_at']}", content),
            )
            n += 1
    except sqlite3.Error:
        pass  # brak tabeli chat_messages (np. świeża baza) — pomijamy

    # 2. Rozwiązane problemy (sprinty) + baza wiedzy (knowledge/)
    root = _repo_root()
    for src, pattern in [("sprint", "docs/sprints/*.md"), ("knowledge", "knowledge/*.md")]:
        for fp in glob.glob(str(root / pattern)):
            try:
                txt = Path(fp).read_text(encoding="utf-8")
            except OSError:
                continue
            con.execute(
                f"INSERT INTO {_FTS}(source,ref,title,content) VALUES(?,?,?,?)",
                (src, os.path.basename(fp), os.path.basename(fp), txt),
            )
            n += 1

    con.commit()
    return n


def search_memory(
    query: str,
    limit: int = 5,
    *,
    workspace_id: Optional[str] = None,
    db_path: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Przeszukaj pamięć (chaty + sprinty + knowledge) po słowach kluczowych. Zwraca
    listę {source, ref, title, snip} posortowaną wg trafności (FTS5 rank)."""
    safe = _fts_query(query)
    if not safe:
        return []
    con = _connect(db_path)
    try:
        reindex(con, workspace_id=workspace_id)  # świeżość — dane małe
        rows = con.execute(
            f"SELECT source, ref, title, snippet({_FTS}, 3, '[', ']', '…', 14) AS snip "
            f"FROM {_FTS} WHERE {_FTS} MATCH ? ORDER BY rank LIMIT ?",
            (safe, limit),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        con.close()


def format_hits(hits: List[Dict[str, Any]]) -> str:
    """Sformatuj trafienia do tekstu dla modelu/użytkownika."""
    if not hits:
        return "Brak trafień w historii rozmów ani w rozwiązanych problemach."
    label = {"chat": "💬 rozmowa", "sprint": "🧱 sprint", "knowledge": "📚 wiedza"}
    lines = ["Znalezione w pamięci historii:"]
    for h in hits:
        src = label.get(h.get("source", ""), h.get("source", ""))
        lines.append(f"- [{src}] {h.get('title', '')}: {h.get('snip', '')}")
    return "\n".join(lines)
