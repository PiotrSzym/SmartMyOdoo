import hashlib
import os
from pathlib import Path
from typing import Optional

from smartmyodoo.swarm.brain.lancedb_client import SHARED_WORKSPACE, LanceDBClient


def _deterministic_id(
    source: str, chunk: str, chunk_idx: int, workspace_id: str
) -> str:
    """Deterministyczne `id` z treści (idempotencja seed — ADR-015).

    Dwukrotny seed tych samych źródeł nie tworzy duplikatów: id zależy od
    treści + source + chunk_idx + workspace_id, więc LanceDB nadpisuje ten sam
    rekord zamiast dokładać nowy z losowym UUID.
    """
    digest = hashlib.sha256(
        f"{workspace_id}\x00{source}\x00{chunk_idx}\x00{chunk}".encode("utf-8")
    ).hexdigest()
    return f"{source}::{chunk_idx}::{digest[:16]}"


def chunk_text(text: str, chunk_size: int = 2000, overlap: int = 200) -> list[str]:
    """Podział tekstu na mniejsze fragmenty (chunks)."""
    if not text:
        return []
    if overlap >= chunk_size:
        raise ValueError(
            f"overlap ({overlap}) must be less than chunk_size ({chunk_size})"
        )

    chunks = []
    start = 0
    text_length = len(text)

    while start < text_length:
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start = end - overlap

    return chunks


def seed_knowledge_base(docs_dir: str, workspace_id: Optional[str] = None):
    """Odczytuje pliki .md i .txt, dzieli na chunki i dodaje do LanceDB.

    ADR-015:
    - `workspace_id=None` → warstwa współdzielona (`SHARED_WORKSPACE`).
    - `workspace_id="<id>"` → warstwa prywatna (np. dane konkretnego klienta).
    Idempotencja: deterministyczne `id` + upsert (usuń istniejące, dodaj na nowo),
    więc dwukrotny seed tych samych źródeł NIE duplikuje rekordów.
    """
    ws = workspace_id or SHARED_WORKSPACE
    print(f"Rozpoczynam seeding bazy wiedzy z katalogu: {docs_dir} (workspace_id={ws})")
    client = LanceDBClient()

    texts = []
    metadatas = []
    ids = []

    for root, _, files in os.walk(docs_dir):
        for file in files:
            if file.endswith((".md", ".txt")):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()

                    source = os.path.relpath(file_path, docs_dir)
                    chunks = chunk_text(content)

                    for i, chunk in enumerate(chunks):
                        texts.append(chunk)
                        metadatas.append({"source": source, "workspace_id": ws})
                        ids.append(_deterministic_id(source, chunk, i, ws))

                    print(f"Przetworzono: {file_path} ({len(chunks)} chunków)")
                except Exception as e:
                    print(f"Błąd czytania {file_path}: {e}")

    if texts:
        # Idempotencja: usuń ewentualne stare wersje tych id przed dodaniem (upsert).
        _delete_existing(client, ids)
        print(f"Dodaję {len(texts)} chunków do LanceDB (workspace_id={ws})...")
        client.add_texts(texts=texts, metadatas=metadatas, ids=ids)
        print("Seeding zakończony.")
    else:
        print("Nie znaleziono dokumentów do seedingu.")


def _delete_existing(client: LanceDBClient, ids: list[str]) -> None:
    """Usuwa rekordy o podanych `id` (upsert-friendly idempotencja).

    Bez tego LanceDB `.add()` dołączałby drugą kopię tego samego chunku przy
    ponownym seedzie. Wartości `id` są kontrolowane (deterministyczny hash),
    ale i tak escapujemy apostrof dla bezpiecznej klauzuli `.where`.
    """
    if client._table is None or not ids:
        return
    safe = ", ".join("'" + i.replace("'", "''") + "'" for i in ids)
    try:
        client._table.delete(f"id IN ({safe})")
    except Exception as e:  # pragma: no cover - zależne od wersji lancedb
        print(f"Ostrzeżenie: nie udało się wyczyścić starych rekordów: {e}")


if __name__ == "__main__":
    import sys

    docs_path = sys.argv[1] if len(sys.argv) > 1 else "docs"
    base_dir = Path(__file__).parent.parent.parent.parent
    full_docs_path = base_dir / docs_path
    seed_knowledge_base(str(full_docs_path))
