import os
import re
import glob
import logging
from typing import Any, Dict, List, Optional

from .lancedb_client import LanceDBClient
from .sqlite_metadata import SQLiteMetadata

logger = logging.getLogger(__name__)

# S5.3: czytelny sygnał, że RAG jest niedostępny (zamiast fabrykowania kontekstu)
DEGRADED_MSG = "[RAG niedostępny — brak kontekstu z Shared Brain (tryb zdegradowany)]"


class SharedBrain:
    """
    API do wprowadzania wiedzy i odpytywania Shared Brain metodą RAG.
    Oplata LanceDB (Wektory) oraz SQLite (Metadane/Cache).
    """

    def __init__(self):
        self.vector_store = LanceDBClient()
        self.metadata_tracker = SQLiteMetadata()

    def retrieve(
        self, query: str, top_k: int = 3, workspace: Optional[str] = None
    ) -> Dict[str, Any]:
        """S5.3: zapytanie RAG ze STRUKTURĄ — niesie flagę `degraded` zamiast zmyślać kontekst.

        Zwraca: {"context": str, "degraded": bool, "hits": int}.
        degraded=True → retrieval niedostępny (Mock/brak bazy); context = jawny komunikat.

        ADR-015: `workspace` (gdy podany) ogranicza wynik do shared ∪ bieżący ws.
        Domyślnie (None) = backward-compat (bez filtra warstw).
        """
        results = self.vector_store.search(query, top_k=top_k, workspace=workspace)
        degraded = bool(getattr(self.vector_store, "degraded", False))

        if not results:
            if degraded:
                return {"context": DEGRADED_MSG, "degraded": True, "hits": 0}
            return {
                "context": "Brak informacji w Shared Brain.",
                "degraded": False,
                "hits": 0,
            }

        context = ""
        for i, res in enumerate(results):
            context += f"\n--- Kontekst {i + 1} (Źródło: {res.get('source')}) ---\n"
            context += res.get("text", "")
            context += "\n"
        return {"context": context, "degraded": degraded, "hits": len(results)}

    def ask_brain(
        self, query: str, top_k: int = 3, workspace: Optional[str] = None
    ) -> str:
        """Główne zapytanie RAG dla Agenta. Zwraca sformatowany tekst kontekstu.

        S5.3: przy degradacji zwraca jawny komunikat (DEGRADED_MSG), nie fabrykuje kontekstu.
        ADR-015: `workspace` przepuszczany do retrieve (izolacja warstw).
        """
        return self.retrieve(query, top_k=top_k, workspace=workspace)["context"]

    def ingest_markdown_file(self, filepath: str):
        """Wczytuje plik MD, sprawdza hashe w SQLite i ładuje wektory do LanceDB."""
        if not os.path.exists(filepath):
            logger.error(f"Plik nie istnieje: {filepath}")
            return

        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        if self.metadata_tracker.is_updated(filepath, content):
            # Proste chunkowanie (w przypadku Markdown dzielimy co np. naglowek, tutaj prosty podzial znakowy dla uproszczenia)
            # Normalnie zastosowalibysmy LangChain TextSplitter
            chunks = self._chunk_text(content, max_length=1000)

            texts = []
            metadatas = []
            ids = []

            for i, chunk in enumerate(chunks):
                texts.append(chunk)
                metadatas.append({"source": filepath})
                ids.append(f"{filepath}_chunk_{i}")

            self.vector_store.add_texts(texts, metadatas, ids)
            self.metadata_tracker.update_record(filepath, content)
            logger.info(f"Zingestowano: {filepath}")
        else:
            logger.info(f"Pominięto (Brak zmian): {filepath}")

    def _chunk_text(
        self, text: str, max_length: int = 1000, overlap: int = 200
    ) -> List[str]:
        """S5.3: chunker z OVERLAPEM po granicach zdań.

        Pakuje zdania do chunków ≤ max_length; sąsiednie chunki współdzielą ogon
        (~overlap znaków) — retrieval nie gubi treści na granicy. Zdania dłuższe niż
        max_length są twardo cięte (fallback). Gwarantuje min. 1 chunk dla niepustego tekstu.
        """
        if not text:
            return []
        overlap = max(0, min(overlap, max_length - 1))
        sentences = re.split(r"(?<=[.!?])\s+", text.strip())

        chunks: List[str] = []
        cur = ""
        for s in sentences:
            # twarde cięcie nadmiarowo długiego zdania
            while len(s) > max_length:
                if cur:
                    chunks.append(cur.strip())
                    cur = ""
                chunks.append(s[:max_length])
                s = s[max_length - overlap :] if overlap else s[max_length:]
            if cur and len(cur) + len(s) + 1 > max_length:
                chunks.append(cur.strip())
                tail = cur[-overlap:] if overlap else ""
                cur = (tail + " " + s).strip() if tail else s
            else:
                cur = (cur + " " + s).strip() if cur else s
        if cur.strip():
            chunks.append(cur.strip())
        return chunks or [text]

    def ingest_directory(self, dir_path: str):
        """Ładuje cały katalog z plikami markdown do Mózgu."""
        md_files = glob.glob(os.path.join(dir_path, "**", "*.md"), recursive=True)
        for filepath in md_files:
            self.ingest_markdown_file(filepath)
