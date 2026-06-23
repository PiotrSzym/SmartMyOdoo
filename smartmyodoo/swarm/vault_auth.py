import logging
import os
from dataclasses import dataclass
from typing import Dict, Any

from smartmyodoo.vault import vault
from smartmyodoo.swarm.pipeline import PipelineError

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PipelineCredentials:
    odoo_url: str
    odoo_db: str
    odoo_login: str
    odoo_password: str
    openrouter_key: str


@dataclass(frozen=True)
class SSHCredentials:
    """Poświadczenia SSH do kontenera brancha odoo.sh (read-only tail logów).

    WIRE-01/D3: host/user/klucz pochodzą WYŁĄCZNIE z vaultu (nie env-plaintext).
    Pola te NIGDY nie są logowane (wzór: db_manager.py:36 — „NIE logujemy creds").
    """

    host: str
    user: str
    key_path: str


class VaultAuthProvider:
    """Adapter pobierający credentials ze SmartMyVault via PIN"""

    @staticmethod
    def _flatten_secrets(data: Dict[str, Any]) -> Dict[str, str]:
        env: Dict[str, str] = {}
        for k, obj in data.items():
            if isinstance(obj, dict):
                if "deleted_at" in obj:
                    continue
                if obj.get("password"):
                    env[f"{k}_PASSWORD"] = str(obj["password"])
                if obj.get("login"):
                    env[f"{k}_LOGIN"] = str(obj["login"])
                if obj.get("api_key"):
                    env[f"{k}_API_KEY"] = str(obj["api_key"])
                if obj.get("url"):
                    env[f"{k}_URL"] = str(obj["url"])
                if obj.get("db"):
                    env[f"{k}_DB"] = str(obj["db"])
                env[k] = str(obj.get("password", ""))
            else:
                env[k] = str(obj)
        return env

    @staticmethod
    def authenticate(pin: str) -> PipelineCredentials:
        try:
            vk = vault.get_vault_key_from_pin(pin, exit_on_fail=False)
            data = vault.load_vault(vk)
        except (vault.VaultDecryptionError, ValueError):
            # Zgodnie z ADR-011: Sanitized message, brak PINu i kluczy w logach
            logger.error(
                "Vault authentication failed due to invalid credentials or corrupted vault."
            )
            raise PipelineError("AUTH failed: Invalid vault credentials.")

        env = VaultAuthProvider._flatten_secrets(data)

        # Wyciąganie wymaganych sekretów
        odoo_url = env.get("ODOO_URL", "http://localhost:8069")
        odoo_db = env.get("ODOO_DB", "")
        odoo_login = env.get("ODOO_LOGIN", "")
        odoo_password = env.get("ODOO_PASSWORD", "")

        openrouter_key = (
            env.get("OPENROUTER_KEY")
            or env.get("OPENROUTER_API_KEY")
            or env.get("OPENROUTER", "")
        )

        # Żadne kluczowe pole nie może być puste.
        if not all([odoo_db, odoo_login, odoo_password, openrouter_key]):
            logger.error(
                "AUTH failed: Brakujące kluczowe sekrety w Vault (ODOO_DB, ODOO_LOGIN, ODOO_PASSWORD lub OPENROUTER_KEY)."
            )
            raise PipelineError("AUTH failed: Missing required secrets in Vault.")

        return PipelineCredentials(
            odoo_url=odoo_url,
            odoo_db=odoo_db,
            odoo_login=odoo_login,
            odoo_password=odoo_password,
            openrouter_key=openrouter_key,
        )

    @staticmethod
    def get_ssh_credentials(pin: str | None = None) -> SSHCredentials:
        """Pobiera poświadczenia SSH do odoo.sh ze SmartMyVault (WIRE-01/D3).

        Sekrety SSH są przechowywane w skarbcu pod kluczem `ODOO_SH_SSH`
        (pola: `host`, `login`/`user`, `key`/`key_path`). Host/user/klucz NIE mogą
        pochodzić z env w plaintext — tylko z vaultu.

        PIN domyślnie z env `VAULT_PIN` (ten sam mechanizm autoryzacji co pipeline).
        Komunikaty błędów są sanityzowane (ADR-011): nie ujawniają PIN-u, ścieżek
        ani treści sekretów.
        """
        pin = pin or os.environ.get("VAULT_PIN")
        if not pin:
            logger.error("SSH AUTH failed: brak PIN-u do skarbca (VAULT_PIN).")
            raise PipelineError("AUTH failed: Missing vault PIN for SSH.")

        try:
            vk = vault.get_vault_key_from_pin(pin, exit_on_fail=False)
            data = vault.load_vault(vk)
        except (vault.VaultDecryptionError, ValueError):
            logger.error(
                "SSH AUTH failed due to invalid credentials or corrupted vault."
            )
            raise PipelineError("AUTH failed: Invalid vault credentials.")

        entry = data.get("ODOO_SH_SSH")
        if not isinstance(entry, dict) or entry.get("deleted_at"):
            logger.error("SSH AUTH failed: brak wpisu ODOO_SH_SSH w skarbcu.")
            raise PipelineError("AUTH failed: Missing SSH secrets in Vault.")

        host = str(entry.get("host") or entry.get("url") or "")
        user = str(entry.get("login") or entry.get("user") or "")
        key_path = str(entry.get("key_path") or entry.get("key") or "")

        if not all([host, user, key_path]):
            # Brak echa wartości — tylko fakt braku pola.
            logger.error(
                "SSH AUTH failed: niekompletny wpis ODOO_SH_SSH (host/user/key)."
            )
            raise PipelineError("AUTH failed: Incomplete SSH secrets in Vault.")

        return SSHCredentials(host=host, user=user, key_path=key_path)
