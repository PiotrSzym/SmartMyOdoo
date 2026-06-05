import os
import tempfile
from unittest.mock import Mock, patch
from smartmyodoo.swarm.brain.sqlite_metadata import SQLiteMetadata
from smartmyodoo.swarm.brain.rag_api import SharedBrain


def test_sqlite_metadata_caching():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.sqlite")
        tracker = SQLiteMetadata(db_path=db_path)

        filepath = "/mock/path/file.md"
        content_v1 = "Hello World"
        content_v2 = "Hello World 2"

        # Na poczatku plik powinien byc zgloszony jako nowy
        assert tracker.is_updated(filepath, content_v1)

        # Zapisujemy
        tracker.update_record(filepath, content_v1)

        # Sprawdzamy ten sam content -> nie wymaga aktualizacji
        assert not tracker.is_updated(filepath, content_v1)

        # Sprawdzamy zmieniony content -> wymaga aktualizacji
        assert tracker.is_updated(filepath, content_v2)


@patch("smartmyodoo.swarm.brain.rag_api.LanceDBClient")
def test_rag_api_flow(mock_lancedb_class):
    # Mockujemy LanceDBClient
    mock_instance = Mock()
    mock_lancedb_class.return_value = mock_instance

    with tempfile.TemporaryDirectory() as tmpdir:
        # Tworzymy tymczasowy plik Markdown
        md_file = os.path.join(tmpdir, "test.md")
        with open(md_file, "w", encoding="utf-8") as f:
            f.write("# Tytul\nTresc dokumentu")

        brain = SharedBrain()
        # Zmieniamy sciezke SQLite zeby nie smiecic
        brain.metadata_tracker.db_path = os.path.join(tmpdir, "meta.sqlite")
        brain.metadata_tracker._init_db()

        # Test 1: Ingest (ładuje do bazy)
        brain.ingest_markdown_file(md_file)
        assert mock_instance.add_texts.call_count == 1

        # Test 2: Ingest tego samego pliku (Pominiecie dzięki SQLite)
        brain.ingest_markdown_file(md_file)
        assert (
            mock_instance.add_texts.call_count == 1
        )  # Wciaz 1, bo plik sie nie zmienil!

        # Test 3: Ask Brain (Zwraca kontekst)
        mock_instance.search.return_value = [
            {"text": "Odpowiedz 1", "source": "src1.md"},
            {"text": "Odpowiedz 2", "source": "src2.md"},
        ]

        answer = brain.ask_brain("Jak dziala Odoo?")
        assert "Odpowiedz 1" in answer
        assert "src2.md" in answer
