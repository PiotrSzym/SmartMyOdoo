import inspect
import logging
import os
import re
import subprocess
from typing import Dict, Any, Callable, List

# Import target functions from MCP and Brain
from smartmyodoo.mcp.server import (
    search_odoo_records,
    read_odoo_schema,
    create_odoo_record,
)
from smartmyodoo.swarm.brain.rag_api import SharedBrain

logger = logging.getLogger(__name__)

TOOL_REGISTRY: Dict[str, Dict[str, Any]] = {}

# WIRE-01/T2a: standardowa ścieżka logu Odoo on-premise (fallback, gdy brak ODOO_LOG_PATH).
_DEFAULT_ODOO_LOG_PATH = "/var/log/odoo/odoo-server.log"
# Limit czasu połączenia SSH (odoo.sh) — nie wisimy w nieskończoność.
_SSH_TIMEOUT_SECONDS = 30

# S1.4: dozwolona nazwa modułu Odoo (blokuje path traversal z wejścia LLM)
_MODULE_NAME_RE = re.compile(r"^[a-z][a-z0-9_]{1,62}$")


def get_type_name(annotation) -> str:
    if annotation is str:
        return "string"
    if annotation is int:
        return "integer"
    if annotation is float:
        return "number"
    if annotation is bool:
        return "boolean"
    if annotation is list or annotation is List:
        return "array"
    if annotation is dict or annotation is Dict:
        return "object"
    return "string"


def _generate_schema(func: Callable) -> Dict[str, Any]:
    """Generates OpenAI function schema via introspection."""
    sig = inspect.signature(func)
    doc = inspect.getdoc(func) or ""

    properties = {}
    required = []

    for name, param in sig.parameters.items():
        if name == "workspace_id":
            continue  # Often injected automatically or default

        prop_schema = {"type": get_type_name(param.annotation)}
        properties[name] = prop_schema
        if param.default == inspect.Parameter.empty:
            required.append(name)

    return {
        "type": "function",
        "function": {
            "name": func.__name__,
            "description": doc.split("\n")[0] if doc else f"Call {func.__name__}",
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        },
    }


def register_tool(name: str):
    """Decorator to register a tool and auto-generate its schema."""

    def decorator(func: Callable):
        schema = _generate_schema(func)
        schema["function"]["name"] = name
        TOOL_REGISTRY[name] = {"callable": func, "schema": schema}
        return func

    return decorator


# --- Wrappers for MCP ---


@register_tool("odoo_search")
def odoo_search(
    model_name: str, domain: str = "[]", fields: str = "[]", limit: int = 10
) -> str:
    """Wyszukaj rekordy w Odoo. Zwraca JSON jako string."""
    import json

    res = search_odoo_records(
        model_name=model_name, domain=domain, fields=fields, limit=limit
    )
    return json.dumps(res, ensure_ascii=False)


@register_tool("odoo_schema")
def odoo_schema(model_name: str) -> str:
    """Pobierz definicje i typy kolumn w konkretnej tabeli Odoo (modelu)."""
    import json

    res = read_odoo_schema(model_name=model_name)
    return json.dumps(res, ensure_ascii=False)


@register_tool("odoo_create")
def odoo_create(model_name: str, values_json: str, reason: str) -> str:
    """Tworzy nowy rekord w Odoo (Shadow Mode). values_json musi być poprawnym JSONem słownika."""
    return create_odoo_record(
        model_name=model_name, values_json=values_json, reason=reason
    )


# --- New Tools ---


@register_tool("rollback_changes")
def rollback_changes(reason: str) -> str:
    """Wymusza wycofanie zmian (rollback) wykonanych w bieżącej transakcji/sandboxie."""
    raise Exception(f"Rollback Triggered by Agent: {reason}")


@register_tool("search_knowledge_base")
def search_knowledge_base(query: str) -> str:
    """Główne zapytanie RAG dostępne dla Agenta. Zwraca sformatowany tekst kontekstu."""
    brain = SharedBrain()
    return brain.ask_brain(query)


@register_tool("scaffold_module")
def scaffold_module(module_name: str) -> str:
    """Tworzy nowy, pusty moduł Odoo w custom_addons/ za pomocą odoo-bin scaffold."""
    try:
        # S1.4: walidacja nazwy (małe litery/cyfry/_, start od litery) — blokada path traversal
        if not _MODULE_NAME_RE.match(module_name or ""):
            return (
                "❌ Niedozwolona nazwa modułu. Dozwolone: małe litery, cyfry, '_', "
                "start od litery (np. 'sprzedaz_raporty')."
            )
        addons_dir = os.path.realpath("custom_addons")
        os.makedirs(addons_dir, exist_ok=True)
        module_dir = os.path.realpath(os.path.join(addons_dir, module_name))
        # belt-and-suspenders: wymuś, że ścieżka pozostaje wewnątrz custom_addons/
        if os.path.commonpath([addons_dir, module_dir]) != addons_dir:
            return "❌ Path traversal zablokowany."
        if os.path.exists(module_dir):
            return f"❌ Moduł '{module_name}' już istnieje."

        os.makedirs(module_dir)
        with open(os.path.join(module_dir, "__manifest__.py"), "w") as f:
            f.write(
                f"{{\n    'name': '{module_name}',\n    'version': '1.0',\n    'depends': ['base'],\n}}\n"
            )
        with open(os.path.join(module_dir, "__init__.py"), "w") as f:
            f.write("")
        return f"✅ Utworzono moduł {module_name} w {addons_dir}"
    except Exception as e:
        return f"❌ Błąd scaffold_module: {str(e)}"


def _read_log_on_premise(lines: int) -> str:
    """WIRE-01/T2a: czyta ostatnie `lines` z pliku logu Odoo (on-premise).

    Ścieżka z env `ODOO_LOG_PATH`, fallback `/var/log/odoo/odoo-server.log`.
    Brak/niedostępny plik → JAWNY błąd z instrukcją (BEZ słowa „symulowane").
    Komunikat NIE ujawnia sekretów — tylko nazwę zmiennej do konfiguracji.
    """
    log_path = os.environ.get("ODOO_LOG_PATH", _DEFAULT_ODOO_LOG_PATH)
    if not os.path.exists(log_path):
        return (
            "❌ Nie znaleziono pliku logu Odoo. Skonfiguruj zmienną środowiskową "
            "ODOO_LOG_PATH wskazującą na log instancji (np. /var/log/odoo/odoo-server.log), "
            "albo zapewnij dostęp do domyślnej ścieżki."
        )
    try:
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.readlines()
            return "".join(content[-lines:])
    except OSError:
        # Nie echujemy ścieżki/treści wyjątku do wyniku (mogą zawierać dane wrażliwe).
        logger.error("Błąd odczytu logu on-premise (ścieżka z ODOO_LOG_PATH).")
        return (
            "❌ Nie udało się odczytać pliku logu Odoo. Sprawdź uprawnienia i wartość "
            "ODOO_LOG_PATH."
        )


def _read_log_odoo_sh(lines: int) -> str:
    """WIRE-01/T2b (D3): SSH `tail -n {lines}` log brancha na odoo.sh.

    Creds (host/user/klucz) z vaultu (NIE env-plaintext). Komenda jako argv-list
    (NIE shell=True) — read-only `tail`. Zero echa creds do logów ani do wyniku
    (wzór: db_manager.py:36).
    """
    # Import lokalny — unikamy cyklu tools↔vault_auth↔pipeline na poziomie modułu.
    from smartmyodoo.swarm.vault_auth import VaultAuthProvider
    from smartmyodoo.swarm.pipeline import PipelineError

    try:
        creds = VaultAuthProvider.get_ssh_credentials()
    except PipelineError:
        # Komunikat sanityzowany — bez treści sekretów.
        logger.error("SSH do odoo.sh nieudane: brak/niepełne poświadczenia w vaultcie.")
        return (
            "❌ Brak poświadczeń SSH do odoo.sh w skarbcu (klucz ODOO_SH_SSH). "
            "Dodaj host/user/key do vaultu, aby pobierać logi brancha."
        )

    # Ścieżka logu na branchu odoo.sh (konfigurowalna; standard odoo.sh).
    remote_log = os.environ.get(
        "ODOO_SH_LOG_PATH", "~/logs/odoo.log"
    )
    # argv-list, ZERO shell=True, ZERO interpolacji user-inputu do shella.
    # `lines` jest int (kontrakt sygnatury) — bezpieczne do str().
    cmd = [
        "ssh",
        "-i",
        creds.key_path,
        "-o",
        "BatchMode=yes",
        "-o",
        "StrictHostKeyChecking=accept-new",
        f"{creds.user}@{creds.host}",
        "tail",
        "-n",
        str(int(lines)),
        remote_log,
    ]
    try:
        # NIE logujemy `cmd` (zawiera host/user/ścieżkę klucza) — wzór db_manager:36.
        res = subprocess.run(
            cmd, capture_output=True, text=True, timeout=_SSH_TIMEOUT_SECONDS
        )
    except (OSError, subprocess.SubprocessError):
        logger.error("SSH do odoo.sh nieudane (połączenie/proces).")
        return "❌ Nie udało się połączyć z odoo.sh przez SSH (sprawdź konfigurację i sieć)."

    if res.returncode != 0:
        # NIE zwracamy stderr w całości (mógłby echować creds/host); skrót diagnostyczny.
        logger.error("SSH tail zwrócił kod != 0 (odoo.sh).")
        return "❌ Zdalne pobranie logu z odoo.sh nie powiodło się (tail zakończony błędem)."
    return res.stdout


@register_tool("read_odoo_log")
def read_odoo_log(lines: int = 50) -> str:
    """Czyta ostatnie 'lines' z logów Odoo (on-premise: plik; odoo.sh: SSH tail)."""
    hosting = (os.environ.get("ODOO_HOSTING") or "").strip().lower()
    if hosting == "odoo_sh":
        return _read_log_odoo_sh(lines)
    return _read_log_on_premise(lines)


@register_tool("search_odoo_code")
def search_odoo_code(regex: str, path: str = "custom_addons") -> str:
    """Wyszukuje regex w kodzie modułów Odoo w podanej ścieżce."""
    try:
        if not os.path.exists(path):
            return f"Ścieżka {path} nie istnieje."
        cmd = ["grep", "-rnE", regex, path]
        res = subprocess.run(cmd, capture_output=True, text=True)
        return res.stdout if res.stdout else "Brak wyników."
    except Exception as e:
        return f"Błąd podczas szukania: {str(e)}"
