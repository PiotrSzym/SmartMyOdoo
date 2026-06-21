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


def test_alembic_downgrade_upgrade_round_trip_is_consistent(tmp_path):
    """RELEASE-01 / T4 (US-REL-4): rollback migracji jest udowodniony.

    Round-trip: upgrade head → downgrade base (schemat usunięty) → upgrade head ponownie.
    Po pełnym cyklu schemat MUSI wrócić do spójnego stanu (te same tabele co po pierwszym
    upgrade). Dowodzi, że `downgrade()` jest poprawny i bezpieczny (ADR-010).

    Wzorzec: subprocess `python -m alembic` (jak test_alembic_upgrade_head_creates_tables) —
    `sys.executable -m alembic` jest odporny na nieaktywowany venv (nota venv-qa-gaps).
    """
    import subprocess
    import sys

    db_path = tmp_path / "roundtrip.db"
    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite:///{db_path}"

    def _alembic(*args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, "-m", "alembic", *args],
            env=env,
            capture_output=True,
            text=True,
            cwd=os.getcwd(),
        )

    def _user_tables() -> set:
        conn = sqlite3.connect(db_path)
        try:
            rows = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name NOT LIKE 'sqlite_%';"
            ).fetchall()
        finally:
            conn.close()
        return {r[0] for r in rows}

    try:
        # 1. upgrade head — schemat tworzony, zapamiętujemy tabele jako referencję.
        r = _alembic("upgrade", "head")
        assert r.returncode == 0, f"upgrade head failed: {r.stderr}"
        tables_after_first_upgrade = _user_tables()
        # Sanity: kluczowe tabele domenowe istnieją (nie sam alembic_version).
        assert {"audit_log", "workspaces", "proposals"} <= tables_after_first_upgrade, (
            f"upgrade head nie utworzył oczekiwanych tabel: {tables_after_first_upgrade}"
        )

        # 2. downgrade base — schemat domenowy usuwany (rollback).
        r = _alembic("downgrade", "base")
        assert r.returncode == 0, f"downgrade base failed: {r.stderr}"
        tables_after_downgrade = _user_tables()
        assert "audit_log" not in tables_after_downgrade, (
            f"downgrade base NIE usunął tabel domenowych: {tables_after_downgrade}"
        )

        # 3. upgrade head ponownie — schemat MUSI wrócić identyczny (spójność round-trip).
        r = _alembic("upgrade", "head")
        assert r.returncode == 0, f"re-upgrade head failed: {r.stderr}"
        tables_after_reupgrade = _user_tables()
        assert tables_after_reupgrade == tables_after_first_upgrade, (
            "Round-trip niespójny: tabele po downgrade→upgrade różnią się od oryginału.\n"
            f"  pierwszy upgrade: {sorted(tables_after_first_upgrade)}\n"
            f"  po round-trip:    {sorted(tables_after_reupgrade)}"
        )
    except FileNotFoundError:
        pytest.fail("Alembic nie jest zainstalowany lub polecenie nie zostało znalezione")


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
