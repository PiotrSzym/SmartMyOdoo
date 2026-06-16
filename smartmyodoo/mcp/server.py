from mcp.server.fastmcp import FastMCP
import os
import sys
import logging

# Dodanie obecnego folderu do sys.path by móc importować lokalne pliki
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from token_governor import governor
import shadow_mode
import database_magic

# Konfiguracja loggera
logger = logging.getLogger(__name__)


class PiiAuditLogFilter(logging.Filter):
    def filter(self, record):
        try:
            # Avoid infinite recursion or circular imports by checking if middleware is initialized
            if pii_middleware_instance is not None and is_pii_enabled("default"):
                middleware = get_pii_middleware()
                if isinstance(record.msg, str):
                    record.msg = middleware.anonymize(record.msg)

                if record.args:
                    new_args = []
                    for arg in record.args:
                        if isinstance(arg, str):
                            new_args.append(middleware.anonymize(arg))
                        else:
                            new_args.append(arg)
                    record.args = tuple(new_args)
        except Exception:
            # If anonymization fails during logging, drop the message or log a safe error
            record.msg = "[PII_SANITIZATION_FAILED] " + str(record.msg)

        return True


logger.addFilter(PiiAuditLogFilter())

# --- PII Middleware Setup ---
from pii_middleware import PiiMiddleware  # noqa: E402

pii_middleware_instance = None


def get_pii_middleware() -> PiiMiddleware:
    global pii_middleware_instance
    if pii_middleware_instance is None:
        pii_middleware_instance = PiiMiddleware()
    return pii_middleware_instance


def is_pii_enabled(workspace_id: str) -> bool:
    env_var = f"PII_ENABLED_{workspace_id.upper()}"
    return os.getenv(env_var, os.getenv("PII_ENABLED_DEFAULT", "True")).lower() in (
        "true",
        "1",
        "yes",
    )


# ----------------------------

# Inicjalizacja serwera MCP dla Odoo
mcp = FastMCP("SmartMyOdoo-MCP")

# Zmienne środowiskowe Odoo
# (UWAGA: Agent nie używa `vault.py` bezpośrednio. Uruchamiamy serwer poprzez: `python vault.py run python odoo_mcp_server/server.py`)
ODOO_URL = os.getenv("ODOO_URL")
ODOO_DB = os.getenv("ODOO_DB")
ODOO_USER = os.getenv("ODOO_USERNAME")
ODOO_PASS = os.getenv("ODOO_PASSWORD")


@mcp.tool()
def check_status() -> str:
    """Sprawdź czy serwer MCP dla Odoo jest włączony i ma dostęp do konfiguracji z Vaulta."""
    status = "✅ Odoo MCP Server is running.\n\n"

    if ODOO_URL and ODOO_DB and ODOO_USER:
        status += f"🔒 SmartMyVault Integration: Aktywna. Wstrzyknięto poświadczenia dla bazy: {ODOO_DB} pod adresem {ODOO_URL}.\n"
    else:
        status += "⚠️ OSTRZEŻENIE: Brak konfiguracji Odoo w zmiennych środowiskowych! Serwer musi zostać uruchomiony przez komendę 'vault run'.\n"

    budget = governor.get_status()
    status += f"💰 Budżet sesji (Token Governor): wydano ${budget['spent_usd']} z dozwolonych ${budget['max_budget_usd']}\n"

    try:
        proposals = shadow_mode.load_proposals()
        pending = len([p for p in proposals if p.get("status") == "pending"])
        approved = len([p for p in proposals if p.get("status") == "approved"])
        status += f"📝 Shadow Mode: {pending} oczekujących propozycji, {approved} gotowych do wykonania.\n"
    except Exception as e:
        logger.error("Błąd odczytu propozycji w check_status: %s", str(e))
        status += "📝 Shadow Mode: Błąd odczytu propozycji (szczegóły w logach)\n"

    return status


@mcp.tool()
def read_odoo_schema(model_name: str, workspace_id: str = "default") -> dict:
    """Pobierz definicje i typy kolumn w konkretnej tabeli Odoo (modelu), np. 'res.partner' lub 'account.move'."""
    try:
        target_odoo = get_odoo_client(workspace_id)
        return target_odoo.get_model_fields(model_name)
    except Exception as e:
        logger.error("Błąd w read_odoo_schema dla %s: %s", model_name, str(e))
        return {
            "error": "Wystąpił błąd podczas pobierania schematu Odoo. Szczegóły w logach systemowych."
        }


@mcp.tool()
def search_odoo_records(
    model_name: str,
    domain: str = "[]",
    fields: str = "[]",
    limit: int = 10,
    workspace_id: str = "default",
) -> dict:
    """
    Wyszukaj rekordy w Odoo.
    Domain to stringifikowana lista list, np. "[['is_company', '=', True]]".
    Fields to stringifikowana lista kolumn, np. "['name', 'email']". Jeśli pusta, zwraca wszystkie.
    """
    import json

    try:
        domain_list = json.loads(domain) if domain else []
        fields_list = json.loads(fields) if fields else []
        target_odoo = get_odoo_client(workspace_id)
        # 'count' = PRAWDZIWA liczba dopasowań (search_count), nie rozmiar strony.
        # Inaczej "ile rekordów?" zwracało domyślny limit (np. 10) zamiast sumy.
        total = target_odoo.search_count(model_name, domain_list)
        records = target_odoo.search_read(model_name, domain_list, fields_list, limit)

        # ADR-012: NIE wkładaj setek pełnych rekordów Odoo do kontekstu LLM. Model
        # potrafi poprosić o limit=1000000 i wszystkie pola → JSON przepełnia okno
        # ("Input too long"). 'count' zostaje DOKŁADNY; do kontekstu trafia próbka.
        # Bonus: ogranicza liczbę wywołań PII (spacy) do MAX_EMBED.
        MAX_EMBED = 50
        embed = records[:MAX_EMBED]

        # PII: anonimizuj WARTOŚCI pól (string), NIE zserializowany JSON. Puszczanie
        # Presidio na całym blobie JSON psuło strukturę (wykrywał URL/DATE obejmujące
        # cudzysłowy/przecinki i podmiana usuwała znaki struktury → json.loads padał).
        if is_pii_enabled(workspace_id):
            pii = get_pii_middleware()
            embed = [
                {
                    k: (
                        pii.anonymize(v, workspace_id=workspace_id)
                        if isinstance(v, str)
                        else v
                    )
                    for k, v in rec.items()
                }
                for rec in embed
            ]

        out: dict = {"records": embed, "count": total}
        if len(embed) < total:
            out["truncated"] = True
            out["note"] = (
                f"Zwrócono próbkę {len(embed)} z {total} rekordów. "
                "Pole 'count' to PEŁNA liczba dopasowań (użyj go do odpowiedzi 'ile')."
            )
        return out
    except Exception as e:
        logger.error("Błąd w search_odoo_records dla %s: %s", model_name, str(e))
        return {
            "error": "Wystąpił błąd podczas wyszukiwania rekordów. Szczegóły w logach systemowych."
        }


@mcp.tool()
def create_odoo_record(
    model_name: str, values_json: str, reason: str, workspace_id: str = "default"
) -> str:
    """
    Tworzy nowy rekord w Odoo (Shadow Mode).
    values_json musi być poprawnym JSONem słownika.
    """
    import json

    try:
        if is_pii_enabled(workspace_id):
            values_json = get_pii_middleware().deanonymize(
                values_json, workspace_id=workspace_id
            )
            reason = get_pii_middleware().deanonymize(reason, workspace_id=workspace_id)

        values = json.loads(values_json)
        proposal = shadow_mode.create_proposal(
            "create", model_name, [], values, reason, workspace_id=workspace_id
        )
        return f"✅ Propozycja (CREATE) zapisana. ID: {proposal['id']}"
    except Exception as e:
        logger.error("Błąd w create_odoo_record dla %s: %s", model_name, str(e))
        return "❌ Błąd zapisu propozycji. Szczegóły w logach systemowych."


@mcp.tool()
def update_odoo_record(
    model_name: str,
    record_id: int,
    values_json: str,
    reason: str,
    workspace_id: str = "default",
) -> str:
    """
    Aktualizuje rekord w Odoo (Shadow Mode).
    values_json musi być poprawnym JSONem słownika.
    """
    import json

    try:
        if is_pii_enabled(workspace_id):
            values_json = get_pii_middleware().deanonymize(
                values_json, workspace_id=workspace_id
            )
            reason = get_pii_middleware().deanonymize(reason, workspace_id=workspace_id)

        values = json.loads(values_json)
        proposal = shadow_mode.create_proposal(
            "update", model_name, [record_id], values, reason, workspace_id=workspace_id
        )
        return f"✅ Propozycja (UPDATE) zapisana. ID: {proposal['id']}"
    except Exception as e:
        logger.error(
            "Błąd w update_odoo_record dla %s (ID %s): %s",
            model_name,
            record_id,
            str(e),
        )
        return "❌ Błąd zapisu propozycji. Szczegóły w logach systemowych."


@mcp.tool()
def delete_odoo_record(
    model_name: str, record_id: int, reason: str, workspace_id: str = "default"
) -> str:
    """
    Usuwa rekord z Odoo (Shadow Mode).
    """
    try:
        if is_pii_enabled(workspace_id):
            reason = get_pii_middleware().deanonymize(reason, workspace_id=workspace_id)

        proposal = shadow_mode.create_proposal(
            "delete", model_name, [record_id], {}, reason, workspace_id=workspace_id
        )
        return f"✅ Propozycja (DELETE) zapisana. ID: {proposal['id']}"
    except Exception as e:
        logger.error(
            "Błąd w delete_odoo_record dla %s (ID %s): %s",
            model_name,
            record_id,
            str(e),
        )
        return "❌ Błąd zapisu propozycji. Szczegóły w logach systemowych."


# KEY-02-3 (ADR-007): import PRZEZ PAKIET, nie przez sys.path-hack ('odoo_client').
# Inaczej powstaje DRUGI obiekt modułu z własną (pustą) ContextVar _odoo_creds_ctx,
# więc poświadczenia wstrzyknięte przez chat.py (set_odoo_creds) nigdy nie docierają
# do narzędzi Odoo. Jeden moduł = jedna ContextVar = creds ze Skarbca działają.
from smartmyodoo.mcp.odoo_client import get_odoo_client  # noqa: E402


@mcp.tool()
def execute_approved_proposals(workspace_id: str = "default") -> str:
    """Wykonuje wszystkie zatwierdzone propozycje (status 'approved') w rzeczywistym systemie Odoo."""
    proposals = shadow_mode.load_proposals(workspace_id=workspace_id)
    approved = [p for p in proposals if p.get("status") == "approved"]

    if not approved:
        return "Brak zatwierdzonych propozycji do wykonania."

    results = []
    for prop in approved:
        try:
            target_odoo = get_odoo_client(prop.get("workspace_id", workspace_id))
            if prop["action_type"] == "create":
                target_odoo.create(prop["model_name"], [prop["values"]])
            elif prop["action_type"] == "update":
                target_odoo.write(
                    prop["model_name"], prop["record_ids"], prop["values"]
                )
            elif prop["action_type"] == "delete":
                target_odoo.unlink(prop["model_name"], prop["record_ids"])

            # Po wykonaniu mozna usunąć propozycję lub oznaczyć jako 'executed'
            db = shadow_mode.SessionLocal()
            db_prop = (
                db.query(shadow_mode.Proposal)
                .filter(shadow_mode.Proposal.id == prop["id"])
                .first()
            )
            if db_prop:
                db_prop.status = "executed"
                db.commit()
            db.close()
            results.append(f"Sukces: Propozycja {prop['id']}")
        except Exception as e:
            logger.error(
                "Błąd podczas wywoływania propozycji %s: %s", prop["id"], str(e)
            )
            results.append(f"Błąd przy propozycji {prop['id']}: (szczegóły w logach)")

    return "\n".join(results)


@mcp.tool()
def propose_magic_fix(
    fix_type: str, record_id: int, reason: str, workspace_id: str = "default"
) -> str:
    """
    Zastosuj "Magię Bazodanową". Pozwala agentowi zażądać wykonania skryptu naprawczego,
    który omija normalne blokady Odoo (np. usunięcie zatwierdzonej faktury, zmiana jednostki miary produktu z historią).
    fix_type musi być jednym z: 'force_cancel_invoice', 'unlock_stock_move', 'change_uom_on_product'.
    """
    try:
        if is_pii_enabled(workspace_id):
            reason = get_pii_middleware().deanonymize(reason, workspace_id=workspace_id)

        proposal = database_magic.propose_magic_fix(
            fix_type, record_id, reason, workspace_id=workspace_id
        )
        return f"🪄 Propozycja Magii Bazodanowej przygotowana. Oczekuje na weryfikację pracownika. ID Propozycji: {proposal['id']}"
    except Exception as e:
        logger.error(
            "Błąd w propose_magic_fix dla typu %s (ID %s): %s",
            fix_type,
            record_id,
            str(e),
        )
        return "❌ Błąd zapisu propozycji magicznej. Szczegóły w logach systemowych."


if __name__ == "__main__":
    # Uruchomienie serwera na standardowym wejściu/wyjściu (stdio) dla integracji z agentem
    mcp.run(transport="stdio")
