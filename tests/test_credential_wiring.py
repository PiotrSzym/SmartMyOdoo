"""KEY-02 / ADR-007: klucz LLM rozwiązywany po typie (resolver), nie po nazwie."""

from pathlib import Path

import smartmyodoo.api  # noqa: F401 — fix cyklu importu przy testach
from smartmyodoo.vault.resolver import resolve_llm_key

_CHAT = (
    Path(__file__).resolve().parents[1] / "smartmyodoo" / "api_routers" / "chat.py"
).read_text(encoding="utf-8")


def test_typed_secret_any_name(monkeypatch):
    monkeypatch.delenv("OPENROUTER_KEY", raising=False)
    v = {
        "moj dowolny klucz": {
            "type": "llm_provider",
            "provider": "openrouter",
            "api_key": "sk-typed",
            "workspace_id": "default",
        }
    }
    assert resolve_llm_key(v) == "sk-typed"


def test_legacy_named_secret(monkeypatch):
    monkeypatch.delenv("OPENROUTER_KEY", raising=False)
    assert resolve_llm_key({"OPENROUTER_KEY": {"api_key": "sk-legacy"}}) == "sk-legacy"


def test_env_fallback(monkeypatch):
    monkeypatch.setenv("OPENROUTER_KEY", "sk-env")
    assert resolve_llm_key({}) == "sk-env"


def test_none_when_absent(monkeypatch):
    monkeypatch.delenv("OPENROUTER_KEY", raising=False)
    assert resolve_llm_key({}) is None


def test_workspace_preference(monkeypatch):
    monkeypatch.delenv("OPENROUTER_KEY", raising=False)
    v = {
        "default key": {
            "type": "llm_provider",
            "provider": "openrouter",
            "api_key": "sk-default",
            "workspace_id": "default",
        },
        "ws key": {
            "type": "llm_provider",
            "provider": "openrouter",
            "api_key": "sk-ws7",
            "workspace_id": "7",
        },
    }
    assert resolve_llm_key(v, workspace_id="7") == "sk-ws7"  # workspace > default


def test_chat_handlers_use_resolver():
    """Strażnik: handlery czatu używają resolve_llm_key, nie get('OPENROUTER_KEY')."""
    assert "resolve_llm_key(" in _CHAT
    assert 'vault_data.get("OPENROUTER_KEY")' not in _CHAT
