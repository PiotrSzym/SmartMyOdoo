"""T1 (DOCKER-01): ENV-owanie ścieżki vaultu przez `VAULT_DIR`.

Powód (D2): mount wolumenu wprost na `smartmyodoo/vault/` przykryłby `vault.py`.
Dlatego ścieżki plików vaultu muszą dać się przekierować na zewnętrzny katalog
(np. `/data/vault` w kontenerze) przez zmienną środowiskową `VAULT_DIR`.

Kontrakt:
- gdy `VAULT_DIR` ustawiony → WSZYSTKIE pliki vaultu (pin/master salt+key, data)
  liczą się od tego katalogu;
- gdy `VAULT_DIR` brak → zachowanie identyczne jak dziś (katalog modułu `vault.py`).

Test ustawia ENV + przeładowuje moduł (importlib.reload), bo stałe ścieżek są
wyliczane raz przy imporcie modułu.
"""

import importlib
import os

from smartmyodoo.vault import vault as _vault


def _reload_vault():
    return importlib.reload(_vault)


def test_vault_dir_env_overrides_all_paths(tmp_path, monkeypatch):
    """Gdy VAULT_DIR wskazuje na tmp_path, wszystkie pochodne ścieżki tam lądują."""
    target = tmp_path / "vault_data_dir"
    monkeypatch.setenv("VAULT_DIR", str(target))
    try:
        vault = _reload_vault()

        assert vault.VAULT_DIR == str(target)
        assert os.path.dirname(vault.PIN_SALT_FILE) == str(target)
        assert os.path.dirname(vault.MASTER_SALT_FILE) == str(target)
        assert os.path.dirname(vault.PIN_KEY_FILE) == str(target)
        assert os.path.dirname(vault.MASTER_KEY_FILE) == str(target)
        assert os.path.dirname(vault.VAULT_DATA_FILE) == str(target)

        # Nazwy plików muszą pozostać niezmienione (kompatybilność wstecz).
        assert os.path.basename(vault.PIN_SALT_FILE) == "pin_salt.cfg"
        assert os.path.basename(vault.MASTER_SALT_FILE) == "master_salt.cfg"
        assert os.path.basename(vault.PIN_KEY_FILE) == "pin_key.enc"
        assert os.path.basename(vault.MASTER_KEY_FILE) == "master_key.enc"
        assert os.path.basename(vault.VAULT_DATA_FILE) == "vault_data.enc"
    finally:
        monkeypatch.delenv("VAULT_DIR", raising=False)
        _reload_vault()


def test_vault_dir_default_is_module_dir(monkeypatch):
    """Bez VAULT_DIR zachowanie identyczne jak dziś: katalog modułu vault.py."""
    monkeypatch.delenv("VAULT_DIR", raising=False)
    vault = _reload_vault()

    expected = os.path.dirname(os.path.abspath(vault.__file__))
    assert vault.VAULT_DIR == expected
    assert vault.VAULT_DATA_FILE == os.path.join(expected, "vault_data.enc")
    assert vault.PIN_SALT_FILE == os.path.join(expected, "pin_salt.cfg")


def test_init_vault_core_writes_into_env_dir(tmp_path, monkeypatch):
    """Realny init zapisuje pliki do katalogu z VAULT_DIR, nie do katalogu modułu."""
    target = tmp_path / "ext_vault"
    target.mkdir()
    monkeypatch.setenv("VAULT_DIR", str(target))
    try:
        vault = _reload_vault()
        vault.init_vault_core("1234", "master-pass-xyz")

        assert (target / "vault_data.enc").exists()
        assert (target / "pin_key.enc").exists()
        assert (target / "master_key.enc").exists()
        assert (target / "pin_salt.cfg").exists()
        assert (target / "master_salt.cfg").exists()
    finally:
        monkeypatch.delenv("VAULT_DIR", raising=False)
        _reload_vault()
