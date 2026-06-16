"""Testy dowodowe SHARE-01-6: vault export/import dla migracji TEJ SAMEJ osoby.

ADR-015: migracja na nową maszynę = zaszyfrowany export/import z PIN/Master,
z jawnym ostrzeżeniem „nie do współdzielenia zespołowego". Sekrety NIGDY nie
trafiają do repo. Round-trip zachowuje dane 1:1.

Testy izolują pliki vault w tmp katalogu (monkeypatch ścieżek modułu vault),
NIGDY nie dotykają realnego `vault_data.enc`.
"""

import importlib
import io

import pytest


@pytest.fixture
def isolated_vault(tmp_path, monkeypatch):
    """Świeży, zainicjalizowany vault w tmp katalogu (PIN=1234, Master=master-pwd)."""
    from smartmyodoo.vault import vault

    monkeypatch.setattr(vault, "VAULT_DIR", str(tmp_path))
    monkeypatch.setattr(vault, "PIN_SALT_FILE", str(tmp_path / "pin_salt.cfg"))
    monkeypatch.setattr(vault, "MASTER_SALT_FILE", str(tmp_path / "master_salt.cfg"))
    monkeypatch.setattr(vault, "PIN_KEY_FILE", str(tmp_path / "pin_key.enc"))
    monkeypatch.setattr(vault, "MASTER_KEY_FILE", str(tmp_path / "master_key.enc"))
    monkeypatch.setattr(vault, "VAULT_DATA_FILE", str(tmp_path / "vault_data.enc"))

    vault.init_vault_core(pin="1234", master="master-pwd")
    return vault


def _store_secret(vault, pin, key, value):
    vk = vault.get_vault_key_from_pin(pin, exit_on_fail=False)
    data = vault.load_vault(vk)
    data[key] = {"password": value, "login": "", "url": "", "db": "", "api_key": ""}
    vault.save_vault(vk, data)


def test_export_import_roundtrip(isolated_vault, tmp_path):
    """US-SHARE-4: export → import zachowuje sekrety 1:1, wymaga PIN."""
    vault = isolated_vault
    _store_secret(vault, "1234", "ODOO", "supersecret")

    export_path = tmp_path / "vault_backup.enc"
    vault.export_vault(str(export_path), pin="1234")
    assert export_path.exists(), "Eksport nie utworzył pliku"

    # blob eksportu MUSI być zaszyfrowany (nie zawiera sekretu plaintext)
    blob = export_path.read_bytes()
    assert b"supersecret" not in blob, "Sekret w plaintext w eksportowanym blobie!"

    # symulacja nowej maszyny: czysty vault, import z tego samego PIN
    fresh_vault = tmp_path / "fresh"
    fresh_vault.mkdir()
    import smartmyodoo.vault.vault as v2

    v2 = importlib.reload(v2)
    v2.VAULT_DIR = str(fresh_vault)
    v2.PIN_SALT_FILE = str(fresh_vault / "pin_salt.cfg")
    v2.MASTER_SALT_FILE = str(fresh_vault / "master_salt.cfg")
    v2.PIN_KEY_FILE = str(fresh_vault / "pin_key.enc")
    v2.MASTER_KEY_FILE = str(fresh_vault / "master_key.enc")
    v2.VAULT_DATA_FILE = str(fresh_vault / "vault_data.enc")

    v2.import_vault(str(export_path), pin="1234")

    vk = v2.get_vault_key_from_pin("1234", exit_on_fail=False)
    restored = v2.load_vault(vk)
    assert restored["ODOO"]["password"] == "supersecret"


def test_import_requires_correct_pin(isolated_vault, tmp_path):
    """Import zaszyfrowanym blobem wymaga poprawnego PIN/Master."""
    vault = isolated_vault
    _store_secret(vault, "1234", "ODOO", "supersecret")

    export_path = tmp_path / "vault_backup.enc"
    vault.export_vault(str(export_path), pin="1234")

    with pytest.raises(vault.VaultDecryptionError):
        vault.import_vault(str(export_path), pin="0000")


def test_export_emits_warning(isolated_vault, tmp_path, capsys):
    """Twarde ostrzeżenie: eksport nie jest do współdzielenia zespołowego."""
    vault = isolated_vault
    _store_secret(vault, "1234", "ODOO", "x")
    export_path = tmp_path / "vault_backup.enc"
    vault.export_vault(str(export_path), pin="1234")
    out = capsys.readouterr().out.lower()
    assert "nie" in out and ("współdziel" in out or "wspoldziel" in out)


def _cp1250_stdout() -> io.TextIOWrapper:
    """Strumień stdout udający domyślną konsolę Windows (cp1250) — jak PowerShell."""
    return io.TextIOWrapper(io.BytesIO(), encoding="cp1250", newline="")


def test_export_no_crash_on_windows_console(isolated_vault, tmp_path, monkeypatch):
    """Finding B (/gf-review): export NIE crashuje na konsoli cp1250, a ostrzeżenie
    ADR-015 REALNIE dociera (kontrola bezpieczeństwa nie może zniknąć w tracebacku)."""
    vault = isolated_vault
    _store_secret(vault, "1234", "ODOO", "x")
    export_path = tmp_path / "vault_backup.enc"

    stream = _cp1250_stdout()
    monkeypatch.setattr("sys.stdout", stream)
    # nie może rzucić UnicodeEncodeError na cp1250
    vault.export_vault(str(export_path), pin="1234")
    stream.flush()
    out = stream.buffer.getvalue().decode("cp1250").lower()

    assert export_path.exists(), "Eksport nie zapisał pliku"
    assert "nie" in out and (
        "współdziel" in out or "wspoldziel" in out
    ), "Ostrzeżenie ADR-015 nie dotarło na konsolę cp1250"


def test_import_no_crash_on_windows_console(isolated_vault, tmp_path, monkeypatch):
    """Finding B: import również nie crashuje na cp1250 (komunikat statusu)."""
    vault = isolated_vault
    _store_secret(vault, "1234", "ODOO", "supersecret")
    export_path = tmp_path / "vault_backup.enc"
    vault.export_vault(str(export_path), pin="1234")

    stream = _cp1250_stdout()
    monkeypatch.setattr("sys.stdout", stream)
    vault.import_vault(
        str(export_path), pin="1234"
    )  # nie może rzucić UnicodeEncodeError
    stream.flush()
    vk = vault.get_vault_key_from_pin("1234", exit_on_fail=False)
    assert vault.load_vault(vk)["ODOO"]["password"] == "supersecret"
