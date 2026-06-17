import hashlib
import os
import re
from pathlib import Path
from typing import Optional

from smartmyodoo.swarm.brain.lancedb_client import SHARED_WORKSPACE, LanceDBClient

# SHARE-02 S2-3: lekki guard-rail PII dla warstwy współdzielonej (NO NEW DEPS).
# Pełny recognizer (Presidio/spacy w `security/pii/`) jest ciężki i wymaga modelu,
# więc do strażnika seedowania używamy prostych, deterministycznych wzorców:
#   - email:  user@domena.tld (bez nazw plików @2x.png / asset-extensions)
#   - NIP:    10 cyfr (ciąg / z myślnikami / spacjami) Z WALIDACJĄ SUMY KONTROLNEJ
# Cel: zatrzymać oczywiste dane klienta przed wejściem do __shared__, nie pełna
# klasyfikacja PII (tę robi warstwa PII na granicy LLM).
#
# SHARE-02 follow-up (/qa+/sec+/gf-review): suma kontrolna NIP eliminuje
# false-positive na dowolnym 10-cyfrowym ciągu (telefon/timestamp/kwota/ID), a
# email-regex pomija odwołania do plików retina/markdown (np. `raport@2x.png`).
_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@([A-Za-z0-9.-]+)\.([A-Za-z]{2,})\b")
# kandydat NIP: 10 cyfr z opcjonalnym separatorem (myślnik/spacja) — checksum niżej
_NIP_CAND_RE = re.compile(r"(?<![\d-])\d{3}[-\s]?\d{3}[-\s]?\d{2}[-\s]?\d{2}(?![\d-])")
_NIP_WEIGHTS = (6, 5, 7, 2, 3, 4, 5, 6, 7)
# rozszerzenia plików, które NIE są domeną e-mail (markdown/asset refs)
_ASSET_EXT = frozenset(
    {
        "png",
        "jpg",
        "jpeg",
        "gif",
        "svg",
        "webp",
        "ico",
        "bmp",
        "css",
        "js",
        "md",
        "txt",
        "html",
    }
)


def _is_valid_nip(digits: str) -> bool:
    """Walidacja sumy kontrolnej polskiego NIP (10 cyfr). Odsiewa losowe 10-cyfrowe
    ciągi (telefon/timestamp/kwota), które NIE są realnym NIP-em."""
    if len(digits) != 10:
        return False
    checksum = sum(int(digits[i]) * _NIP_WEIGHTS[i] for i in range(9)) % 11
    return checksum != 10 and checksum == int(digits[9])


def _has_email(text: str) -> bool:
    for m in _EMAIL_RE.finditer(text):
        domain, tld = m.group(1), m.group(2).lower()
        if tld in _ASSET_EXT:
            continue  # `@2x.png`, `logo@3x.svg` — to nazwy plików, nie e-mail
        if re.fullmatch(r"\d+x", domain):
            continue  # retina suffix (`@2x`, `@3x`) bez prawdziwej domeny
        return True
    return False


def _has_nip(text: str) -> bool:
    for m in _NIP_CAND_RE.finditer(text):
        if _is_valid_nip(re.sub(r"\D", "", m.group(0))):
            return True
    return False


def detect_pii(text: str) -> bool:
    """Zwraca True, gdy `text` wygląda na PII (email lub NIP z poprawną sumą kontrolną).
    Lekki, bez zależności.

    Świadomie konserwatywny: lepiej oznaczyć i pominąć (z opcją --allow-pii-shared),
    niż po cichu wpuścić dane klienta do warstwy współdzielonej. Suma kontrolna NIP
    i wykluczenie nazw plików ograniczają fałszywe alarmy bez nowych zależności.
    """
    if not text:
        return False
    return _has_email(text) or _has_nip(text)


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


def seed_knowledge_base(
    docs_dir: str,
    workspace_id: Optional[str] = None,
    allow_pii_shared: bool = False,
):
    """Odczytuje pliki .md i .txt, dzieli na chunki i dodaje do LanceDB.

    ADR-015:
    - `workspace_id=None` → warstwa współdzielona (`SHARED_WORKSPACE`).
    - `workspace_id="<id>"` → warstwa prywatna (np. dane konkretnego klienta).
    Idempotencja: deterministyczne `id` + upsert (usuń istniejące, dodaj na nowo),
    więc dwukrotny seed tych samych źródeł NIE duplikuje rekordów.

    SHARE-02 S2-3 (guard PII shared): gdy seedujemy do warstwy WSPÓŁDZIELONEJ
    (`workspace_id is None`), chunki wyglądające na PII (NIP/email) są POMIJANE
    z głośnym ostrzeżeniem — chyba że `allow_pii_shared=True`. Warstwy prywatne
    NIE są filtrowane (dane klienta w jego workspace są w porządku).
    """
    ws = workspace_id or SHARED_WORKSPACE
    is_shared = workspace_id is None
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

                    added = 0
                    for i, chunk in enumerate(chunks):
                        # Guard PII tylko dla warstwy współdzielonej.
                        if is_shared and not allow_pii_shared and detect_pii(chunk):
                            print(
                                f"[!] OSTRZEŻENIE PII: chunk {i} z '{source}' wygląda "
                                "na dane osobowe (NIP/email) — POMINIĘTY w warstwie "
                                "__shared__. Użyj --allow-pii-shared, by wymusić, "
                                "lub seeduj do warstwy prywatnej (--private --workspace)."
                            )
                            continue
                        texts.append(chunk)
                        metadatas.append({"source": source, "workspace_id": ws})
                        ids.append(_deterministic_id(source, chunk, i, ws))
                        added += 1

                    print(f"Przetworzono: {file_path} ({added}/{len(chunks)} chunków)")
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
