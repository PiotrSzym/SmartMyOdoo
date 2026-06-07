import inspect
import os
import subprocess
from typing import Dict, Any, Callable, List

# Import target functions from MCP and Brain
from smartmyodoo.mcp.server import (
    search_odoo_records,
    read_odoo_schema,
    create_odoo_record,
)
from smartmyodoo.swarm.brain.rag_api import SharedBrain

TOOL_REGISTRY: Dict[str, Dict[str, Any]] = {}


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
        addons_dir = os.path.join("custom_addons")
        os.makedirs(addons_dir, exist_ok=True)
        module_dir = os.path.join(addons_dir, module_name)
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


@register_tool("read_odoo_log")
def read_odoo_log(lines: int = 50) -> str:
    """Czyta ostatnie 'lines' z pliku logów Odoo (symulowane)."""
    log_path = "odoo.log"
    if not os.path.exists(log_path):
        return f"Plik {log_path} nie istnieje."
    try:
        with open(log_path, "r", encoding="utf-8") as f:
            content = f.readlines()
            return "".join(content[-lines:])
    except Exception as e:
        return f"Błąd czytania logów: {str(e)}"


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
