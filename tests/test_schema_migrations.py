import os
import sqlite3
import pytest
from unittest.mock import patch

from smartmyodoo.core.database import backup_before_migrate


def test_alembic_upgrade_head_creates_tables(tmp_path):
    """
    Testuje czy uruchomienie alembic upgrade head poprawnie tworzy strukturę bazy.
    Wykorzystuje subprocess do wywołania polecenia alembic.
    """
    import subprocess
    import sys

    # Kopiujemy ewentualne pliki alembic jeśli istnieją, ale w fazie RED ich nie ma.
    # Wywołujemy alembic upgrade head na tymczasowej bazie
    db_path = tmp_path / "test.db"

    # Konfigurujemy env z URL bazy, aby alembic użył go z env var (zależnie od implementacji alembic.ini)
    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite:///{db_path}"

    try:
        # `python -m alembic` zamiast gołego `alembic` — odporne na nieaktywowany venv
        # (gdy katalog bin venv nie jest na PATH subprocessu).
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            env=env,
            capture_output=True,
            text=True,
            cwd=os.getcwd(),
        )

        # Oczekujemy, że kod zakończenia to 0 (sukces)
        assert result.returncode == 0, f"Alembic failed: {result.stderr}"

        # Sprawdzamy czy plik bazy został utworzony
        assert db_path.exists()

        # Podłączamy się do bazy i weryfikujemy czy są tabele, np. alembic_version
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Przykładowe tabele wspomniane w architekturze
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='alembic_version';"
        )
        assert cursor.fetchone() is not None, "Tabela alembic_version nie istnieje"

        # Wymagane przez architekturę (HLD)
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='audit_log';"
        )
        assert cursor.fetchone() is not None, "Tabela audit_log nie istnieje"

        conn.close()
    except FileNotFoundError:
        pytest.fail(
            "Alembic nie jest zainstalowany lub polecenie nie zostało znalezione"
        )


def test_backup_before_migrate_creates_backup(tmp_path):
    """
    Testuje mechanizm backup-before-migrate: kopiowanie pliku bazy do .bak.{timestamp} przed migracją.
    Oczekujemy retencji max 3 plików.
    """
    db_file = tmp_path / "smartmyodoo.db"
    db_file.write_text("dummy database content")

    with patch("smartmyodoo.core.database.DB_PATH", f"sqlite:///{db_file}"):
        # Symulujemy 4 kolejne backupy (retencja ma wynosić max 3)
        for i in range(4):
            backup_before_migrate()
            import time

            time.sleep(0.01)  # dla różnych timestampów

        bak_files = list(tmp_path.glob("smartmyodoo.db.bak.*"))
        assert len(bak_files) > 0, "Plik backupu nie został utworzony"
        assert (
            len(bak_files) == 3
        ), f"Zła retencja plików: znaleziono {len(bak_files)} zamiast 3"
