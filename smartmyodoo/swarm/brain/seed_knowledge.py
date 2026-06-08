import os
import uuid
from pathlib import Path
from smartmyodoo.swarm.brain.lancedb_client import LanceDBClient


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


def seed_knowledge_base(docs_dir: str):
    """Odczytuje pliki .md i .txt, dzieli na chunki i dodaje do LanceDB."""
    print(f"Rozpoczynam seeding bazy wiedzy z katalogu: {docs_dir}")
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

                    # Chunking
                    chunks = chunk_text(content)

                    for i, chunk in enumerate(chunks):
                        texts.append(chunk)
                        metadatas.append(
                            {"source": os.path.relpath(file_path, docs_dir)}
                        )
                        ids.append(f"{uuid.uuid4()}-{i}")

                    print(f"Przetworzono: {file_path} ({len(chunks)} chunków)")
                except Exception as e:
                    print(f"Błąd czytania {file_path}: {e}")

    if texts:
        print(f"Dodaję {len(texts)} chunków do LanceDB...")
        client.add_texts(texts=texts, metadatas=metadatas, ids=ids)
        print("Seeding zakończony.")
    else:
        print("Nie znaleziono dokumentów do seedingu.")


if __name__ == "__main__":
    import sys

    docs_path = sys.argv[1] if len(sys.argv) > 1 else "docs"
    base_dir = Path(__file__).parent.parent.parent.parent
    full_docs_path = base_dir / docs_path
    seed_knowledge_base(str(full_docs_path))
