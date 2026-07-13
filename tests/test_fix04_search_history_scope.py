"""FIX-04 T3 (A-3): izolacja pamięci historii per-workspace przez search_history.

Bramka Fazy 3 audytu: chat z przestrzeni A NIE może wyciec do search_history
wołanego w przestrzeni B. Sprinty/wiedza (knowledge) pozostają GLOBALNE (D4).

Ścieżka egzekwowana: executor wstrzykuje workspace_id (WORKSPACE_SCOPED_TOOLS) →
search_history(query, workspace_id) → search_memory(workspace_id=…) → filtr TYLKO
na chat_messages.
"""

import sqlite3

import pytest

from smartmyodoo.swarm.tools import TOOL_REGISTRY


@pytest.fixture
def seeded_db(tmp_path):
    """Baza z czatami w dwóch przestrzeniach (A=default, B=myodooTest)."""
    path = str(tmp_path / "hist.db")
    con = sqlite3.connect(path)
    con.execute(
        "CREATE TABLE chat_messages (id INTEGER PRIMARY KEY, workspace_id TEXT, "
        "session_id TEXT, role TEXT, content TEXT, created_at TEXT)"
    )
    rows = [
        ("default", "sA", "user", "tajny_kontrahent_alfa w przestrzeni A", "2026-07-10 10:00"),
        ("myodooTest", "sB", "user", "notatka_beta w przestrzeni B", "2026-07-10 11:00"),
    ]
    con.executemany(
        "INSERT INTO chat_messages(workspace_id,session_id,role,content,created_at) "
        "VALUES (?,?,?,?,?)",
        rows,
    )
    con.commit()
    con.close()
    return path


def _search(query, workspace_id, db, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db}")
    return TOOL_REGISTRY["search_history"]["callable"](query=query, workspace_id=workspace_id)


def test_search_history_accepts_workspace_id():
    """Tool ma parametr workspace_id (wstrzykiwany przez executor), ale NIE w schemacie LLM."""
    import inspect

    sig = inspect.signature(TOOL_REGISTRY["search_history"]["callable"])
    assert "workspace_id" in sig.parameters
    # schema pomija workspace_id (LLM go nie podaje — injection po stronie executora)
    schema_props = TOOL_REGISTRY["search_history"]["schema"]["function"]["parameters"]["properties"]
    assert "workspace_id" not in schema_props
    assert "query" in schema_props


def test_chat_from_other_workspace_does_not_leak(seeded_db, monkeypatch):
    """Czat z A NIE pojawia się w search_history przestrzeni B (twarda izolacja)."""
    out_b = _search("tajny_kontrahent_alfa", "myodooTest", seeded_db, monkeypatch)
    assert "tajny_kontrahent_alfa" not in out_b, "czat z obcej przestrzeni wyciekł do B"


def test_chat_visible_in_own_workspace(seeded_db, monkeypatch):
    """Ten sam czat JEST widoczny w swojej przestrzeni (A=default)."""
    out_a = _search("tajny_kontrahent_alfa", "default", seeded_db, monkeypatch)
    assert "tajny_kontrahent_alfa" in out_a.lower() or "alfa" in out_a.lower()


def test_sprints_stay_global(seeded_db, monkeypatch):
    """Sprinty (rozwiązane problemy) pozostają globalne — widoczne z KAŻDEJ przestrzeni."""
    # hasło z realnego sprintu FIX-04 (ten plik żyje w docs/sprints/)
    out_b = _search("parytet polityk", "myodooTest", seeded_db, monkeypatch)
    assert "sprint" in out_b.lower() or "parytet" in out_b.lower(), (
        "sprinty powinny być globalne (D4), a nie zniknąć przy filtrze workspace"
    )
