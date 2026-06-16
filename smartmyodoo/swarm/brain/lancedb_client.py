import os
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

# Warstwa współdzielona (ADR-015): rekordy bez jawnego workspace_id.
SHARED_WORKSPACE = "__shared__"


class LanceDBClient:
    """
    Klient wbudowanej bazy wektorowej LanceDB.
    Wykorzystuje modele sentence-transformers do osadzania tekstu (np. all-MiniLM-L6-v2).
    """

    def __init__(
        self,
        db_path: Optional[str] = None,
        model_name: str = "all-MiniLM-L6-v2",
    ):
        # ADR-015: ścieżka indeksu jest lokalna/gitignored. Pozwalamy nadpisać
        # ją zmienną środowiskową (np. seed w Dockerze/CLI na izolowany store).
        if db_path is None:
            db_path = os.environ.get(
                "SMARTMYODOO_LANCEDB_PATH", ".agents/lancedb_store"
            )
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
                # Backward-compat (ADR-015): stara tabela bez `workspace_id`
                # → dodaj kolumnę z defaultem SHARED_WORKSPACE, bez utraty wierszy.
                self._migrate_workspace_column()
            else:
                schema = pa.schema(
                    [
                        pa.field("id", pa.string()),
                        pa.field("vector", pa.list_(pa.float32(), 384)),
                        pa.field("text", pa.string()),
                        pa.field("source", pa.string()),
                        pa.field("workspace_id", pa.string()),
                    ]
                )
                self._table = self._db.create_table(table_name, schema=schema)
                logger.info(f"Utworzono nową tabelę wektorową: {table_name}")

        except ImportError as e:
            logger.warning(
                f"Zależności do wektoryzacji nie są zainstalowane: {e}. Klient w trybie Mock."
            )

    def _migrate_workspace_column(self):
        """Backward-compat (ADR-015): dodaj `workspace_id` do starej tabeli.

        Stary schemat to `{id, vector, text, source}` bez izolacji warstw.
        Po migracji wszystkie istniejące wiersze należą do warstwy współdzielonej
        (`SHARED_WORKSPACE`), zgodnie z zasadą „braki = __shared__". Operacja jest
        idempotentna — gdy kolumna już istnieje, nic nie robimy.
        """
        if self._table is None:
            return
        try:
            field_names = {f.name for f in self._table.schema}
            if "workspace_id" in field_names:
                return
            # LanceDB add_columns: nowa kolumna z wartością domyślną (SQL literal).
            self._table.add_columns({"workspace_id": f"'{SHARED_WORKSPACE}'"})
            logger.info(
                "Migracja: dodano kolumnę 'workspace_id' "
                f"(default '{SHARED_WORKSPACE}') do tabeli knowledge_base."
            )
        except Exception as e:  # pragma: no cover - zależne od wersji lancedb
            logger.warning(f"Migracja workspace_id nieudana: {e}")

    def add_texts(
        self, texts: List[str], metadatas: List[Dict[str, Any]], ids: List[str]
    ):
        """Wektoryzuje teksty i dodaje do LanceDB."""
        # is None (NIE truthiness) — pusta tabela LanceDB ma len==0 i była mylona z atrapą.
        if self._table is None or self._model is None:
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
                    # ADR-015: brak workspace_id w metadanych = warstwa współdzielona.
                    "workspace_id": metadatas[i].get("workspace_id", SHARED_WORKSPACE),
                }
            )

        self._table.add(data)
        logger.info(f"Dodano {len(data)} rekordów do LanceDB.")

    @property
    def degraded(self) -> bool:
        """True TYLKO gdy brak realnej bazy/modelu (np. brak zależności) — tryb Mock.

        Używamy `is None`, NIE truthiness: pusta tabela LanceDB (0 wierszy) ma len==0,
        więc `not self._table` błędnie raportowało brak połączenia dla niezasianej bazy.
        Pusta baza = połączona, search zwraca [] (brak wiedzy), to NIE degradacja.
        """
        return self._table is None or self._model is None

    @staticmethod
    def _escape_ws(workspace: str) -> str:
        """Sanityzacja wartości workspace dla klauzuli LanceDB `.where()`.

        Wartość trafia do literału SQL w pojedynczych apostrofach. Zgodnie z
        SQL escapujemy apostrof przez jego podwojenie (`'` → `''`), co zapobiega
        wstrzyknięciu (np. `ws' OR '1'='1`). Nie pozwalamy ominąć izolacji warstw.
        """
        return str(workspace).replace("'", "''")

    def search(
        self, query: str, top_k: int = 3, workspace: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Przeszukuje bazę po podobieństwie semantycznym.

        ADR-015: gdy podano `workspace`, zwracamy wyłącznie warstwę współdzieloną
        (`SHARED_WORKSPACE`) ∪ rekordy bieżącego `workspace` — NIGDY cudze prywatne.
        Domyślnie (`workspace=None`) zachowujemy backward-compat: brak filtra.

        S5.3: w trybie zdegradowanym (Mock — brak bazy/modelu) zwraca PUSTĄ listę,
        zamiast fabrykować fałszywy kontekst ('Mocked RAG response'). Sygnalizację
        degradacji niesie właściwość `degraded` (sprawdzana wyżej w SharedBrain.retrieve).
        """
        if self.degraded:
            logger.warning("[RAG] tryb zdegradowany — brak retrievalu (zwracam []).")
            return []

        assert self._model is not None and self._table is not None  # nosec B101
        query_vector = self._model.encode([query])[0]
        search_q = self._table.search(query_vector.tolist())

        if workspace is not None:
            ws = self._escape_ws(workspace)
            shared = self._escape_ws(SHARED_WORKSPACE)
            search_q = search_q.where(
                f"workspace_id = '{shared}' OR workspace_id = '{ws}'"
            )

        results = search_q.limit(top_k).to_list()
        return results
