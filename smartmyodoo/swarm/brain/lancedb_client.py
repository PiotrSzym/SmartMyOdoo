import os
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class LanceDBClient:
    """
    Klient wbudowanej bazy wektorowej LanceDB.
    Wykorzystuje modele sentence-transformers do osadzania tekstu (np. all-MiniLM-L6-v2).
    """

    def __init__(
        self,
        db_path: str = ".agents/lancedb_store",
        model_name: str = "all-MiniLM-L6-v2",
    ):
        self.db_path = db_path
        self.model_name = model_name
        self._db = None
        self._table = None
        self._model = None

        # Lazy initialization
        self._init_db()

    def _init_db(self):
        try:
            import lancedb
            from sentence_transformers import SentenceTransformer
            import pyarrow as pa

            os.makedirs(self.db_path, exist_ok=True)
            self._db = lancedb.connect(self.db_path)

            # Wczytywanie modelu osadzania (Embedding Model)
            self._model = SentenceTransformer(self.model_name)

            # Definiowanie schematu dla tabeli knowledge_base
            # Embeddings wymiar zalezy od modelu (all-MiniLM-L6-v2 ma 384)
            # W lancedb definiujemy dane początkowe lub schemat, aby utworzyć tabelę
            table_name = "knowledge_base"

            if table_name in self._db.table_names():
                self._table = self._db.open_table(table_name)
            else:
                schema = pa.schema(
                    [
                        pa.field("id", pa.string()),
                        pa.field("vector", pa.list_(pa.float32(), 384)),
                        pa.field("text", pa.string()),
                        pa.field("source", pa.string()),
                    ]
                )
                self._table = self._db.create_table(table_name, schema=schema)
                logger.info(f"Utworzono nową tabelę wektorową: {table_name}")

        except ImportError as e:
            logger.warning(
                f"Zależności do wektoryzacji nie są zainstalowane: {e}. Klient w trybie Mock."
            )

    def add_texts(
        self, texts: List[str], metadatas: List[Dict[str, Any]], ids: List[str]
    ):
        """Wektoryzuje teksty i dodaje do LanceDB."""
        if not self._table or not self._model:
            logger.warning("Mock: add_texts called.")
            return

        embeddings = self._model.encode(texts)

        data = []
        for i, text in enumerate(texts):
            data.append(
                {
                    "id": ids[i],
                    "vector": embeddings[i].tolist(),
                    "text": text,
                    "source": metadatas[i].get("source", "unknown"),
                }
            )

        self._table.add(data)
        logger.info(f"Dodano {len(data)} rekordów do LanceDB.")

    @property
    def degraded(self) -> bool:
        """True gdy brak realnej bazy/modelu (tryb Mock) — retrieval niedostępny."""
        return not self._table or not self._model

    def search(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """Przeszukuje bazę po podobieństwie semantycznym.

        S5.3: w trybie zdegradowanym (Mock — brak bazy/modelu) zwraca PUSTĄ listę,
        zamiast fabrykować fałszywy kontekst ('Mocked RAG response'). Sygnalizację
        degradacji niesie właściwość `degraded` (sprawdzana wyżej w SharedBrain.retrieve).
        """
        if self.degraded:
            logger.warning("[RAG] tryb zdegradowany — brak retrievalu (zwracam []).")
            return []

        assert self._model is not None and self._table is not None  # nosec B101
        query_vector = self._model.encode([query])[0]
        results = self._table.search(query_vector.tolist()).limit(top_k).to_list()
        return results
