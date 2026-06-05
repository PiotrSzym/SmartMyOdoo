import sqlite3
import hashlib
import os
import logging

logger = logging.getLogger(__name__)


class SQLiteMetadata:
    """
    Zarządza bazą SQLite śledzącą metadane i hashe plików,
    aby unikać wielokrotnego ładowania do bazy wektorowej.
    """

    def __init__(self, db_path: str = ".agents/brain_metadata.sqlite"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS file_cache (
                    filepath TEXT PRIMARY KEY,
                    file_hash TEXT NOT NULL,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
        finally:
            conn.close()

    def _compute_hash(self, text: str) -> str:
        return hashlib.md5(text.encode("utf-8"), usedforsecurity=False).hexdigest()

    def is_updated(self, filepath: str, content: str) -> bool:
        """
        Sprawdza czy plik uległ zmianie od ostatniej wektoryzacji.
        Zwraca True, jeśli wymaga ponownego załadowania.
        """
        current_hash = self._compute_hash(content)
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT file_hash FROM file_cache WHERE filepath = ?", (filepath,)
            )
            row = cursor.fetchone()
            if row is None:
                return True
            return row[0] != current_hash
        finally:
            conn.close()

    def update_record(self, filepath: str, content: str):
        """Zapisuje nowy hash pliku po udanej wektoryzacji."""
        current_hash = self._compute_hash(content)
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                """
                INSERT OR REPLACE INTO file_cache (filepath, file_hash, last_updated)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            """,
                (filepath, current_hash),
            )
            conn.commit()
            logger.info(f"Zaktualizowano metadane dla {filepath}")
        finally:
            conn.close()
