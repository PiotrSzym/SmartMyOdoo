import xmlrpc.client  # nosec B411
import os
import asyncio
import contextvars
import logging
from typing import Any, Dict, Optional, Set

logger = logging.getLogger(__name__)


class OdooFieldError(Exception):
    """TRUST-01 T3 (D4): pole nie istnieje w tym modelu/wersji Odoo.

    FAIL LOUD — lepszy jawny błąd niż ciche puste wyniki (które napędzały
    nieufność: zapytanie o pole z innej wersji zwracało pustkę bez ostrzeżenia).
    """

    pass

# KEY-02-3 (ADR-007): poświadczenia Odoo per workspace ze Skarbca, wstrzykiwane na czas
# obsługi żądania (ContextVar — bezpieczne dla współbieżności, propaguje się do asyncio.to_thread).
# Format: {workspace_id: {"url","db","username","password"}}. Mają PIERWSZEŃSTWO nad ENV.
_odoo_creds_ctx: "contextvars.ContextVar[Optional[Dict[str, Dict[str, str]]]]" = (
    contextvars.ContextVar("odoo_creds", default=None)
)


def set_odoo_creds(creds: Optional[Dict[str, Dict[str, str]]]) -> None:
    """Ustawia poświadczenia Odoo dla bieżącego żądania (per workspace). None = wyczyść."""
    _odoo_creds_ctx.set(creds)


class OdooClient:
    """Klient API dla Odoo (XML-RPC). Poświadczenia: Skarbiec per workspace (ContextVar)
    z pierwszeństwem, w razie braku — zmienne środowiskowe (tryb `vault run`)."""

    def __init__(self, workspace_id: str = "default"):
        self.workspace_id = workspace_id

        ctx = _odoo_creds_ctx.get() or {}
        c = ctx.get(workspace_id) or ctx.get("default") or {}

        prefix = (
            f"PROJECT_HUB_{workspace_id.upper()}_ODOO"
            if workspace_id != "default"
            else "ODOO"
        )
        # Skarbiec (ctx) > ENV
        self.url = c.get("url") or os.getenv(f"{prefix}_URL") or os.getenv("ODOO_URL")
        self.db = c.get("db") or os.getenv(f"{prefix}_DB") or os.getenv("ODOO_DB")
        self.username = (
            c.get("username")
            or os.getenv(f"{prefix}_USERNAME")
            or os.getenv("ODOO_USERNAME")
            or os.getenv(f"{prefix}_LOGIN")
            or os.getenv("ODOO_LOGIN")
        )
        self.password = (
            c.get("password")
            or os.getenv(f"{prefix}_PASSWORD")
            or os.getenv("ODOO_PASSWORD")
        )
        self.uid: Optional[int] = None
        self.models: Any = None
        # TRUST-01 T3 (D3): wersja wykryta RAZ przy connect i cache'owana (per instancja
        # klienta = per workspace, bo fabryka tworzy świeży klient na żądanie).
        self.version_info: Optional[Dict[str, Any]] = None
        self.major: Optional[int] = None
        # fields_get cache per model (D3): nie odpytujemy schematu co request.
        self._fields_cache: Dict[str, Set[str]] = {}

    def connect(self):
        """Uwierzytelnia się w Odoo i zwraca True w przypadku sukcesu.

        TRUST-01 T3: dodatkowo wykrywa wersję serwera (common.version()) — wzorzec
        z swarm/recon.py:36, przeniesiony do connectora czatu. Wykrycie wersji jest
        NIE-KRYTYCZNE: gdy version() padnie, logujemy i lecimy dalej (auth ważniejszy).
        """
        if not all([self.url, self.db, self.username, self.password]):
            raise ValueError("Brak konfiguracji Odoo w zmiennych środowiskowych.")

        common = xmlrpc.client.ServerProxy("{}/xmlrpc/2/common".format(self.url))
        self.uid = common.authenticate(self.db, self.username, self.password, {})

        if not self.uid:
            raise PermissionError(
                "Błąd autoryzacji do Odoo. Sprawdź poświadczenia w SmartMyVault."
            )

        # TRUST-01 T3 (D3): wykryj wersję raz przy connect (wzorzec recon.py).
        try:
            self.version_info = common.version()
            svi = (self.version_info or {}).get("server_version_info")
            if isinstance(svi, (list, tuple)) and svi:
                self.major = int(svi[0])
            else:
                # Fallback: sparsuj prefiks ze 'server_version' (np. '19.0').
                sv = str((self.version_info or {}).get("server_version", ""))
                head = sv.split(".")[0]
                self.major = int(head) if head.isdigit() else None
        except Exception as e:  # noqa: BLE001 — wersja jest dodatkiem, nie blokerem
            logger.warning("Nie udało się wykryć wersji Odoo: %s", type(e).__name__)
            self.version_info = None
            self.major = None

        self.models = xmlrpc.client.ServerProxy("{}/xmlrpc/2/object".format(self.url))
        return True

    def get_available_fields(self, model: str) -> Set[str]:
        """Zwraca zbiór nazw pól modelu (z `fields_get`), cache'owany per model (D3).

        Dzięki temu lista pól jest świadoma wersji Odoo — pola hardkodowane spoza
        danej wersji wykrywamy ZANIM odpytamy serwer (patrz validate_fields)."""
        if model in self._fields_cache:
            return self._fields_cache[model]
        if not self.uid:
            self.connect()
        fields_info = self.models.execute_kw(
            self.db, self.uid, self.password, model, "fields_get", [], {"attributes": []}
        )
        names: Set[str] = set(fields_info.keys()) if isinstance(fields_info, dict) else set()
        self._fields_cache[model] = names
        return names

    def validate_fields(self, model: str, fields: list) -> None:
        """TRUST-01 T3 (D4): waliduje, że pola istnieją w danej wersji modelu.

        Pole nieobecne (np. analytic_account_id na v19) => OdooFieldError (FAIL LOUD)
        + log z wersją. NIGDY ciche puste wyniki."""
        available = self.get_available_fields(model)
        missing = [f for f in (fields or []) if f not in available]
        if missing:
            logger.error(
                "Pola %s nie istnieją w modelu %s (Odoo major=%s). FAIL LOUD (D4).",
                missing,
                model,
                self.major,
            )
            raise OdooFieldError(
                f"Pola {missing} nie istnieją w modelu '{model}' "
                f"(Odoo {self.major}). Sprawdź wersję — pola różnią się między 16/18/19."
            )

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

    def search_count(self, model: str, domain: list) -> int:
        """Zwraca PRAWDZIWĄ liczbę rekordów pasujących do domeny (niezależnie od limitu
        strony). Bez tego 'ile rekordów?' zwracało rozmiar strony (np. 10), nie sumę."""
        if not self.uid:
            self.connect()
        return self.models.execute_kw(
            self.db, self.uid, self.password, model, "search_count", [domain]
        )

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


def get_odoo_client(workspace_id: str = "default") -> OdooClient:
    """Fabryka klientów Odoo dla konkretnego workspace.

    KEY-02-3 (ADR-007): ZAWSZE buduje świeży klient — __init__ czyta wtedy bieżącą
    ContextVar (poświadczenia ze Skarbca wstrzyknięte na czas żądania). Wcześniej dla
    'default' zwracaliśmy singleton zbudowany w czasie importu (puste creds), przez co
    poświadczenia per-żądanie nigdy nie docierały. Świeży klient = brak wycieku uid/
    połączenia między żądaniami i workspace'ami (multi-tenant).
    """
    return OdooClient(workspace_id=workspace_id)
