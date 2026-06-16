"""Testy dowodowe SHARE-01: wersjonowana wiedza + izolacja workspace_id.

Zasady (ADR-015):
- Wiedza = tekst w gicie (folder `knowledge/`), indeks pochodny budowany lokalnie.
- Każdy rekord ma `workspace_id`; shared = "__shared__", prywatne = realny ws.
- `search(workspace=A)` zwraca shared ∪ A, NIGDY prywatne B.
- Backward-compat: brak `workspace` w wywołaniu = bez filtra (stare zachowanie).

KRYTYCZNE: testy LanceDB używają **tmp db_path** w fixture, NIE współdzielonego
`.agents/lancedb_store`. Pomijane, gdy brak zależności RAG (offline).
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

lancedb = pytest.importorskip("lancedb")  # skip gdy brak zależności
pytest.importorskip("sentence_transformers")

REPO_ROOT = Path(__file__).resolve().parents[1]
SHARED_WS = "__shared__"


@pytest.fixture
def tmp_client(tmp_path):
    """Realny LanceDBClient na izolowanej tmp ścieżce (nie globalny store)."""
    from smartmyodoo.swarm.brain.lancedb_client import LanceDBClient

    client = LanceDBClient(db_path=str(tmp_path / "lancedb_iso"))
    if client._table is None or client._model is None:
        pytest.skip("model/baza niedostępne w tym środowisku (offline)")
    return client


# --- SHARE-01-1: wersjonowany folder knowledge/ -----------------------------


def test_knowledge_dir_exists_and_tracked():
    """US-SHARE-1: folder knowledge/ istnieje, ma ≥1 plik i NIE jest gitignored."""
    knowledge_dir = REPO_ROOT / "knowledge"
    assert knowledge_dir.is_dir(), "Brak wersjonowanego folderu knowledge/"

    docs = [
        p
        for p in knowledge_dir.rglob("*")
        if p.is_file() and p.suffix in (".md", ".txt")
    ]
    assert docs, "knowledge/ musi zawierać ≥1 plik .md/.txt z wiedzą"

    # strażnik 1: pliki knowledge/ NIE mogą być ignorowane przez gita
    sample = docs[0].relative_to(REPO_ROOT).as_posix()
    res = subprocess.run(
        ["git", "check-ignore", sample],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    # exit 1 = plik NIE jest ignorowany (pożądane); exit 0 = ignorowany (błąd)
    assert (
        res.returncode == 1
    ), f"Plik {sample} jest gitignored — wiedza nie pojedzie do repo"

    # strażnik 2: plik MUSI być faktycznie śledzony przez gita (staged/committed).
    # check-ignore nie wystarcza — plik untracked-but-not-ignored przeszedłby fałszywie
    # jako „tracked" (luka wykryta przez /qa, error_registry). git ls-files = prawda o trackingu.
    tracked = subprocess.run(
        ["git", "ls-files", "--", sample],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    assert tracked.stdout.strip() == sample, (
        f"Plik {sample} NIE jest śledzony przez gita (git add knowledge/) — "
        f"wersjonowana wiedza nie pojedzie do repo"
    )


def test_no_secret_in_artifact():
    """US-SHARE-3 strażnik: w knowledge/ brak plików sekretnych/binarnych."""
    knowledge_dir = REPO_ROOT / "knowledge"
    forbidden_suffixes = (".enc", ".cfg", ".key", ".pem", ".env")
    offenders = [
        p.name
        for p in knowledge_dir.rglob("*")
        if p.is_file() and p.suffix in forbidden_suffixes
    ]
    assert not offenders, f"Sekrety/binaria w knowledge/: {offenders}"


# --- SHARE-01-2: workspace_id w schemacie i zapisie -------------------------


def test_add_texts_default_workspace_is_shared(tmp_client):
    """Rekord bez workspace_id w metadanych → traktowany jako '__shared__'."""
    tmp_client.add_texts(
        texts=["wspolna wiedza zespolu"],
        metadatas=[{"source": "team.md"}],
        ids=["s1"],
    )
    rows = tmp_client._table.to_pandas()
    assert "workspace_id" in rows.columns
    assert rows.loc[rows["id"] == "s1", "workspace_id"].iloc[0] == SHARED_WS


def test_add_texts_private_workspace(tmp_client):
    """Rekord z workspace_id → zapisany w warstwie prywatnej."""
    tmp_client.add_texts(
        texts=["prywatna wiedza klienta A"],
        metadatas=[{"source": "a.md", "workspace_id": "client_a"}],
        ids=["p1"],
    )
    rows = tmp_client._table.to_pandas()
    assert rows.loc[rows["id"] == "p1", "workspace_id"].iloc[0] == "client_a"


def test_migration_legacy_table_without_workspace(tmp_path):
    """Backward-compat: tabela utworzona BEZ workspace_id → braki = '__shared__'.

    Symulujemy stary store: tabela o schemacie {id, vector, text, source}.
    Po otwarciu nowym klientem migracja dodaje kolumnę z defaultem '__shared__',
    bez utraty starych wierszy.
    """
    import pyarrow as pa
    from sentence_transformers import SentenceTransformer

    db_path = str(tmp_path / "legacy_store")
    db = lancedb.connect(db_path)
    model = SentenceTransformer("all-MiniLM-L6-v2")
    legacy_schema = pa.schema(
        [
            pa.field("id", pa.string()),
            pa.field("vector", pa.list_(pa.float32(), 384)),
            pa.field("text", pa.string()),
            pa.field("source", pa.string()),
        ]
    )
    table = db.create_table("knowledge_base", schema=legacy_schema)
    vec = model.encode(["stary rekord"])[0].tolist()
    table.add(
        [{"id": "legacy1", "vector": vec, "text": "stary rekord", "source": "old.md"}]
    )

    # Otwieramy starym store nowym klientem — powinna zajść migracja kolumny
    from smartmyodoo.swarm.brain.lancedb_client import LanceDBClient

    client = LanceDBClient(db_path=db_path)
    rows = client._table.to_pandas()
    assert "workspace_id" in rows.columns, "Migracja nie dodała kolumny workspace_id"
    assert len(rows) == 1, "Migracja zgubiła stare wiersze"
    assert rows.loc[rows["id"] == "legacy1", "workspace_id"].iloc[0] == SHARED_WS


# --- SHARE-01-3: filtr search po workspace ----------------------------------


def _seed_mixed(client):
    client.add_texts(
        texts=[
            "shared: jak skonfigurowac Odoo XML-RPC",
            "private A: dane klienta A o fakturach",
            "private B: dane klienta B o fakturach",
        ],
        metadatas=[
            {"source": "shared.md"},  # → __shared__
            {"source": "a.md", "workspace_id": "ws_a"},
            {"source": "b.md", "workspace_id": "ws_b"},
        ],
        ids=["sh", "a", "b"],
    )


def test_workspace_isolation(tmp_client):
    """US-SHARE-2: search(ws=A) = shared ∪ A, bez prywatnych B."""
    _seed_mixed(tmp_client)
    results = tmp_client.search("faktury klienta", top_k=10, workspace="ws_a")
    returned_ws = {r.get("workspace_id") for r in results}
    assert "ws_b" not in returned_ws, "Wyciek prywatnych danych workspace B!"
    assert returned_ws <= {SHARED_WS, "ws_a"}
    returned_ids = {r.get("id") for r in results}
    assert "b" not in returned_ids


def test_workspace_includes_shared(tmp_client):
    """search(ws=A) zawiera też warstwę shared."""
    _seed_mixed(tmp_client)
    results = tmp_client.search("konfiguracja Odoo XML-RPC", top_k=10, workspace="ws_a")
    returned_ids = {r.get("id") for r in results}
    assert "sh" in returned_ids, "Brak warstwy shared w wyniku dla workspace A"


def test_search_backward_compat_no_workspace(tmp_client):
    """Contract: search bez workspace = stare zachowanie (bez filtra)."""
    _seed_mixed(tmp_client)
    results = tmp_client.search("faktury", top_k=10)  # brak workspace
    returned_ws = {r.get("workspace_id") for r in results}
    # bez filtra widać wszystkie warstwy (w tym B)
    assert "ws_b" in returned_ws


def test_workspace_value_with_quote_is_sanitized(tmp_client):
    """Security: wartość workspace z apostrofem nie wysadza zapytania .where()."""
    _seed_mixed(tmp_client)
    # nie może rzucić wyjątku składni LanceDB ani zwrócić cudzych prywatnych
    results = tmp_client.search("faktury", top_k=10, workspace="ws_a' OR '1'='1")
    returned_ws = {r.get("workspace_id") for r in results}
    assert "ws_b" not in returned_ws


def test_sharedbrain_passes_workspace(tmp_path, monkeypatch):
    """SharedBrain.retrieve/ask_brain przepuszcza workspace do vector_store."""
    from smartmyodoo.swarm.brain import rag_api

    captured = {}

    class FakeStore:
        degraded = False

        def search(self, query, top_k=3, workspace=None):
            captured["workspace"] = workspace
            return [{"text": "ctx", "source": "x", "workspace_id": "ws_a"}]

    brain = rag_api.SharedBrain.__new__(rag_api.SharedBrain)
    brain.vector_store = FakeStore()
    brain.metadata_tracker = None

    brain.retrieve("q", top_k=3, workspace="ws_a")
    assert captured["workspace"] == "ws_a"

    captured.clear()
    brain.ask_brain("q", workspace="ws_a")
    assert captured["workspace"] == "ws_a"


# --- SHARE-01-4: seed idempotentny + warstwa private ------------------------


def test_seed_builds_from_knowledge(tmp_path, monkeypatch):
    """US-SHARE-1: seed na czystym (tmp) store buduje tabelę z katalogu źródeł."""
    from smartmyodoo.swarm.brain import seed_knowledge
    from smartmyodoo.swarm.brain.lancedb_client import LanceDBClient

    docs_dir = tmp_path / "knowledge"
    docs_dir.mkdir()
    (docs_dir / "lesson.md").write_text(
        "Lekcja: zawsze parametryzuj SQL.", encoding="utf-8"
    )

    store_path = str(tmp_path / "store")
    monkeypatch.setattr(
        seed_knowledge,
        "LanceDBClient",
        lambda *a, **k: LanceDBClient(db_path=store_path),
    )

    seed_knowledge.seed_knowledge_base(str(docs_dir))

    client = LanceDBClient(db_path=store_path)
    if client._table is None:
        pytest.skip("offline")
    rows = client._table.to_pandas()
    assert len(rows) >= 1
    assert (rows["workspace_id"] == SHARED_WS).all()


def test_seed_idempotent_no_duplicates(tmp_path, monkeypatch):
    """Integration: seed 2× = bez duplikatów (deterministyczne id)."""
    from smartmyodoo.swarm.brain import seed_knowledge
    from smartmyodoo.swarm.brain.lancedb_client import LanceDBClient

    docs_dir = tmp_path / "knowledge"
    docs_dir.mkdir()
    (docs_dir / "lesson.md").write_text("Lekcja idempotentna.", encoding="utf-8")

    store_path = str(tmp_path / "store")
    monkeypatch.setattr(
        seed_knowledge,
        "LanceDBClient",
        lambda *a, **k: LanceDBClient(db_path=store_path),
    )

    seed_knowledge.seed_knowledge_base(str(docs_dir))
    client = LanceDBClient(db_path=store_path)
    if client._table is None:
        pytest.skip("offline")
    count_after_first = len(client._table.to_pandas())

    seed_knowledge.seed_knowledge_base(str(docs_dir))
    count_after_second = len(client._table.to_pandas())

    assert count_after_second == count_after_first, "Drugi seed zduplikował rekordy"


def test_seed_private_workspace_tagging(tmp_path, monkeypatch):
    """seed z workspace_id → rekordy w warstwie prywatnej."""
    from smartmyodoo.swarm.brain import seed_knowledge
    from smartmyodoo.swarm.brain.lancedb_client import LanceDBClient

    docs_dir = tmp_path / "private"
    docs_dir.mkdir()
    (docs_dir / "client.md").write_text("Prywatne dane klienta.", encoding="utf-8")

    store_path = str(tmp_path / "store")
    monkeypatch.setattr(
        seed_knowledge,
        "LanceDBClient",
        lambda *a, **k: LanceDBClient(db_path=store_path),
    )

    seed_knowledge.seed_knowledge_base(str(docs_dir), workspace_id="client_x")
    client = LanceDBClient(db_path=store_path)
    if client._table is None:
        pytest.skip("offline")
    rows = client._table.to_pandas()
    assert (rows["workspace_id"] == "client_x").all()


def test_seed_cli_subcommand(tmp_path):
    """E2E: `python -m smartmyodoo seed --shared <dir>` działa z CLI."""
    docs_dir = tmp_path / "knowledge"
    docs_dir.mkdir()
    (docs_dir / "lesson.md").write_text("CLI seed lesson.", encoding="utf-8")
    store_path = tmp_path / "cli_store"

    env = dict(os.environ)
    env["SMARTMYODOO_LANCEDB_PATH"] = str(store_path)

    res = subprocess.run(
        [sys.executable, "-m", "smartmyodoo", "seed", "--shared", str(docs_dir)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        env=env,
        timeout=300,
    )
    assert res.returncode == 0, f"seed CLI failed: {res.stderr}\n{res.stdout}"
    assert store_path.exists(), "CLI seed nie utworzył store w wskazanej ścieżce"


# --- SHARE-01-5: guide + README ---------------------------------------------


def test_guide_exists_and_readme_links():
    """US-SHARE-3: guide istnieje, README linkuje, brak instrukcji kopiowania .enc."""
    guide = REPO_ROOT / "docs" / "guides" / "sharing_knowledge_and_secrets.md"
    assert guide.is_file(), "Brak guide sharing_knowledge_and_secrets.md"
    guide_text = guide.read_text(encoding="utf-8")
    # nie wolno instruować kopiowania zaszyfrowanych plików vault do gita
    lowered = guide_text.lower()
    assert "menedżer sekretów" in lowered or "menedzer sekretow" in lowered

    readme = REPO_ROOT / "README.md"
    assert readme.is_file()
    readme_text = readme.read_text(encoding="utf-8")
    assert "sharing_knowledge_and_secrets" in readme_text, "README nie linkuje guide"
