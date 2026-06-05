import os
import glob
import logging
from .lancedb_client import LanceDBClient
from .sqlite_metadata import SQLiteMetadata

logger = logging.getLogger(__name__)


class SharedBrain:
    """
    API do wprowadzania wiedzy i odpytywania Shared Brain metodą RAG.
    Oplata LanceDB (Wektory) oraz SQLite (Metadane/Cache).
    """

    def __init__(self):
        self.vector_store = LanceDBClient()
        self.metadata_tracker = SQLiteMetadata()

    def ask_brain(self, query: str, top_k: int = 3) -> str:
        """
        Główne zapytanie RAG dostępne dla Agenta. Zwraca sformatowany tekst kontekstu.
        """
        results = self.vector_store.search(query, top_k=top_k)

        if not results:
            return "Brak informacji w Shared Brain."

        context = ""
        for i, res in enumerate(results):
            context += f"\n--- Kontekst {i+1} (Źródło: {res.get('source')}) ---\n"
            context += res.get("text", "")
            context += "\n"

        return context

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

    def _chunk_text(self, text: str, max_length: int = 1000):
        """Prymitywny chunker."""
        return [text[i : i + max_length] for i in range(0, len(text), max_length)]

    def ingest_directory(self, dir_path: str):
        """Ładuje cały katalog z plikami markdown do Mózgu."""
        md_files = glob.glob(os.path.join(dir_path, "**", "*.md"), recursive=True)
        for filepath in md_files:
            self.ingest_markdown_file(filepath)
