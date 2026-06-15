"""K2 (KEY-01): resolver po typie + auto-tag legacy.

Dowód: 100 dowolnie nazwanych kluczy → trafiamy po TYPIE/provider/workspace, nie po nazwie;
stare sekrety (OPENROUTER_KEY, <ws>_ODOO) działają dalej (auto-tag).
"""

from smartmyodoo.vault.schemas import CredentialType
from smartmyodoo.vault.resolver import resolve_credential, to_credential


def test_legacy_openrouter_autotag():
    vault = {"OPENROUTER_KEY": {"api_key": "sk-or-LEGACY"}}
    c = resolve_credential(vault, CredentialType.LLM_PROVIDER)
    assert c is not None and c.provider == "openrouter" and c.api_key == "sk-or-LEGACY"


def test_legacy_odoo_autotag_per_workspace():
    vault = {
        "smartTest_ODOO": {
            "url": "https://t",
            "db": "t",
            "login": "u",
            "password": "p",
        },
    }
    c = resolve_credential(vault, CredentialType.ODOO_DATA, workspace_id="smartTest")
    assert c is not None and c.workspace_id == "smartTest" and c.db == "t"


def test_resolve_llm_by_provider_among_many():
    # dowolne nazwy — liczy się typ+provider, nie nazwa
    vault = {
        "klucz_a": {"type": "llm_provider", "provider": "openrouter", "api_key": "A"},
        "moj_drugi": {"type": "llm_provider", "provider": "anthropic", "api_key": "B"},
        "9879879": {"password": "smiec"},  # nieklasyfikowalny — ignorowany
    }
    a = resolve_credential(vault, CredentialType.LLM_PROVIDER, provider="anthropic")
    assert a is not None and a.api_key == "B"


def test_workspace_preferred_over_default():
    vault = {
        "def": {
            "type": "odoo_data",
            "workspace_id": "default",
            "url": "u",
            "db": "d",
            "login": "l",
        },
        "ws7": {
            "type": "odoo_data",
            "workspace_id": "7",
            "url": "u7",
            "db": "d7",
            "login": "l7",
        },
    }
    c = resolve_credential(vault, CredentialType.ODOO_DATA, workspace_id="7")
    assert c is not None and c.workspace_id == "7"


def test_unclassifiable_returns_none():
    assert to_credential("nazwa 1", {"password": "x"}) is None
    assert (
        to_credential(
            "deleted",
            {
                "type": "llm_provider",
                "provider": "x",
                "api_key": "y",
                "deleted_at": "2026-01-01",
            },
        )
        is None
    )
