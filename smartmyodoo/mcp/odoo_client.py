import xmlrpc.client  # nosec B411
import os
import asyncio
from typing import Any, Optional


class OdooClient:
    """Klient API dla Odoo korzystający z XML-RPC. Inicjalizuje się zmiennymi ze środowiska (SmartMyVault)."""

    def __init__(self, workspace_id: str = "default"):
        self.workspace_id = workspace_id
        prefix = (
            f"PROJECT_HUB_{workspace_id.upper()}_ODOO"
            if workspace_id != "default"
            else "ODOO"
        )

        self.url = os.getenv(f"{prefix}_URL") or os.getenv("ODOO_URL")
        self.db = os.getenv(f"{prefix}_DB") or os.getenv("ODOO_DB")
        self.username = (
            os.getenv(f"{prefix}_USERNAME")
            or os.getenv("ODOO_USERNAME")
            or os.getenv(f"{prefix}_LOGIN")
            or os.getenv("ODOO_LOGIN")
        )
        self.password = os.getenv(f"{prefix}_PASSWORD") or os.getenv("ODOO_PASSWORD")
        self.uid: Optional[int] = None
        self.models: Any = None

    def connect(self):
        """Uwierzytelnia się w Odoo i zwraca True w przypadku sukcesu."""
        if not all([self.url, self.db, self.username, self.password]):
            raise ValueError("Brak konfiguracji Odoo w zmiennych środowiskowych.")

        common = xmlrpc.client.ServerProxy("{}/xmlrpc/2/common".format(self.url))
        self.uid = common.authenticate(self.db, self.username, self.password, {})

        if not self.uid:
            raise PermissionError(
                "Błąd autoryzacji do Odoo. Sprawdź poświadczenia w SmartMyVault."
            )

        self.models = xmlrpc.client.ServerProxy("{}/xmlrpc/2/object".format(self.url))
        return True

    def search_read(
        self, model: str, domain: list, fields: Optional[list] = None, limit: int = 10
    ):
        """Wyszukuje i czyta rekordy z podanego modelu."""
        if not self.uid:
            self.connect()

        # Wymuszenie twardego limitu (ADR-012)
        safe_limit = min(limit, 500) if limit else 500

        kwargs: dict[str, Any] = {}
        if fields:
            kwargs["fields"] = fields
        kwargs["limit"] = safe_limit

        records = self.models.execute_kw(
            self.db, self.uid, self.password, model, "search_read", [domain], kwargs
        )
        return records

    def get_model_fields(self, model: str):
        """Pobiera strukturę (schemat) danego modelu."""
        if not self.uid:
            self.connect()

        fields_info = self.models.execute_kw(
            self.db,
            self.uid,
            self.password,
            model,
            "fields_get",
            [],
            {"attributes": ["string", "help", "type"]},
        )
        return fields_info

    def create(self, model: str, vals_list: list):
        """Tworzy nowe rekordy w podanym modelu."""
        if not self.uid:
            self.connect()

        return self.models.execute_kw(
            self.db, self.uid, self.password, model, "create", [vals_list], {}
        )

    def write(self, model: str, ids: list, vals: dict):
        """Aktualizuje istniejące rekordy."""
        if not self.uid:
            self.connect()

        return self.models.execute_kw(
            self.db, self.uid, self.password, model, "write", [ids, vals], {}
        )

    def unlink(self, model: str, ids: list):
        """Usuwa (kasuje) istniejące rekordy."""
        if not self.uid:
            self.connect()

        return self.models.execute_kw(
            self.db, self.uid, self.password, model, "unlink", [ids], {}
        )

    # --- WRAppery ASYNC ---

    async def connect_async(self):
        return await asyncio.to_thread(self.connect)

    async def search_read_async(
        self, model: str, domain: list, fields: Optional[list] = None, limit: int = 10
    ):
        return await asyncio.to_thread(self.search_read, model, domain, fields, limit)

    async def get_model_fields_async(self, model: str):
        return await asyncio.to_thread(self.get_model_fields, model)

    async def create_async(self, model: str, vals_list: list):
        return await asyncio.to_thread(self.create, model, vals_list)

    async def write_async(self, model: str, ids: list, vals: dict):
        return await asyncio.to_thread(self.write, model, ids, vals)

    async def unlink_async(self, model: str, ids: list):
        return await asyncio.to_thread(self.unlink, model, ids)


# Globalna instancja klienta (domyślny workspace)
odoo = OdooClient()


def get_odoo_client(workspace_id: str = "default") -> OdooClient:
    """Fabryka klientów Odoo dla konkretnego workspace."""
    if workspace_id == "default":
        return odoo
    return OdooClient(workspace_id=workspace_id)
