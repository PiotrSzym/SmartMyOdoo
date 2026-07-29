"""WSISO-01 — testy DOWODOWE: koniec cichego fallbacku poświadczeń Odoo do `default`.

Niezmiennik: tylko workspace `default` dziedziczy Odoo (default-cred / legacy
`default_ODOO` / ENV). Konkretnie wybrany nie-`default` workspace bez własnego
`ODOO_DATA` → jawny błąd, NIGDY instancja innego workspace (bug live grfood→myodoo).

RED (dowód, że wektory istniały — potwierdzone na kodzie sprzed fixu, sonda /dev):
  V1 resolve_credential(grfood) → default(myodoo);  V2 _resolve_odoo_creds(grfood) →
  default_ODOO(myodoo);  V3 OdooClient("default") po inject grfood → myodoo url.

Wzorzec: mock granicy sieci nie jest tu potrzebny — testujemy WYBÓR poświadczeń,
nie połączenie. Styl ContextVar z tests/test_odoo_creds_context.py.
"""

import pytest

from smartmyodoo.vault.schemas import CredentialType
from smartmyodoo.vault.resolver import resolve_credential, resolve_llm_key
from smartmyodoo.mcp.odoo_client import (
    OdooClient,
    OdooWorkspaceUnconfigured,
    set_odoo_creds,
    set_odoo_unconfigured,
)


MYODOO_URL = "https://myodoo.odoo.com"
GRFOOD_URL = "https://gfit.com.pl"


@pytest.fixture(autouse=True)
def _reset_odoo_ctx():
    """Higiena ContextVar: żaden test nie może zostawić creds/markera dla następnego
    (contextvars trwają w obrębie wątku pytest)."""
    yield
    set_odoo_creds(None)
    set_odoo_unconfigured(None)


def _vault_default_only_typed():
    """Vault: TYLKO `default` ma Odoo (myodoo). grfood nie ma własnego ODOO_DATA."""
    return {
        "default_ODOO": {
            "type": "odoo_data",
            "workspace_id": "default",
            "url": MYODOO_URL,
            "db": "myodoo",
            "login": "admin",
            "api_key": "KEY-MYODOO",
        }
    }


def _vault_default_only_legacy():
    """Vault legacy (bez pola `type`): tylko `default_ODOO` (myodoo)."""
    return {
        "default_ODOO": {
            "url": MYODOO_URL,
            "db": "myodoo",
            "login": "admin",
            "password": "pass-myodoo",
        }
    }


def _vault_grfood_has_own():
    """Vault: grfood MA własny ODOO_DATA (gfit) + default (myodoo)."""
    return {
        "default_ODOO": {
            "type": "odoo_data",
            "workspace_id": "default",
            "url": MYODOO_URL,
            "db": "myodoo",
            "login": "admin",
            "api_key": "KEY-MYODOO",
        },
        "grfood_ODOO": {
            "type": "odoo_data",
            "workspace_id": "grfood",
            "url": GRFOOD_URL,
            "db": "gfitdb",
            "login": "svc_smo",
            "api_key": "KEY-GRFOOD",
        },
    }


# ── T1 (V1): resolve_credential — allow_default_fallback ──────────────────────


def test_t1_nondefault_without_creds_returns_none_no_fallback():
    """GREEN: nie-default bez własnego ODOO_DATA + allow_default_fallback=False → None
    (NIE default/myodoo). RED przed fixem: zwracało default(myodoo)."""
    c = resolve_credential(
        _vault_default_only_typed(),
        CredentialType.ODOO_DATA,
        workspace_id="grfood",
        allow_default_fallback=False,
    )
    assert c is None


def test_t1_vector_proof_legacy_fallback_still_leaks_by_default():
    """Dowód, że wektor V1 istniał: DOMYŚLNIE (allow_default_fallback=True) resolver
    nadal dziedziczy default — to zachowanie POTRZEBNE dla LLM (klucz globalny), ale
    dla Odoo wołający MUSZĄ podać False (co robi _inject_odoo_creds/_resolve_odoo_creds)."""
    c = resolve_credential(
        _vault_default_only_typed(),
        CredentialType.ODOO_DATA,
        workspace_id="grfood",
    )
    assert c is not None and c.workspace_id == "default" and c.url == MYODOO_URL


def test_t1_default_workspace_still_resolves_with_no_fallback():
    """Regres: ws=`default` z allow_default_fallback=False nadal dostaje default (exact match)."""
    c = resolve_credential(
        _vault_default_only_typed(),
        CredentialType.ODOO_DATA,
        workspace_id="default",
        allow_default_fallback=False,
    )
    assert c is not None and c.url == MYODOO_URL


def test_t1_nondefault_with_own_creds_resolves_own():
    """Nie-default z własnym ODOO_DATA (grfood/gfit) → jego własne creds, nie myodoo."""
    c = resolve_credential(
        _vault_grfood_has_own(),
        CredentialType.ODOO_DATA,
        workspace_id="grfood",
        allow_default_fallback=False,
    )
    assert c is not None and c.workspace_id == "grfood" and c.url == GRFOOD_URL


def test_t1_regres_llm_key_still_falls_back_to_default():
    """Regres KRYTYCZNY: resolve_llm_key (klucz globalny) NADAL dziedziczy z default —
    reguła WSISO-01 wyłącza LLM. grfood bez własnego klucza → klucz z default."""
    vault = {"OPENROUTER_KEY": {"api_key": "sk-or-GLOBAL"}}  # workspace default (autotag)
    key = resolve_llm_key(vault, workspace_id="grfood")
    assert key == "sk-or-GLOBAL"


# ── T2 (V2): workspaces._resolve_odoo_creds — legacy default_ODOO tylko dla default ──


def test_t2_nondefault_missing_creds_raises_400_with_ws_name():
    """GREEN: grfood bez grfood_ODOO, jest default_ODOO → HTTPException 400 z nazwą ws.
    RED przed fixem: zwracało default_ODOO (myodoo) bez błędu (cross-client)."""
    from fastapi import HTTPException
    from smartmyodoo.api_routers.workspaces import _resolve_odoo_creds

    with pytest.raises(HTTPException) as ei:
        _resolve_odoo_creds(_vault_default_only_legacy(), "grfood")
    assert ei.value.status_code == 400
    assert "grfood" in ei.value.detail
    # Sanityzacja: komunikat NIE ujawnia URL/hasła instancji default
    assert MYODOO_URL not in ei.value.detail
    assert "pass-myodoo" not in ei.value.detail


def test_t2_default_still_uses_default_odoo_legacy():
    """Regres: ws=`default` nadal dostaje default_ODOO (myodoo)."""
    from smartmyodoo.api_routers.workspaces import _resolve_odoo_creds

    creds = _resolve_odoo_creds(_vault_default_only_legacy(), "default")
    assert creds.get("url") == MYODOO_URL


def test_t2_nondefault_with_own_creds_ok():
    """Nie-default z własnym sekretem → jego dane (gfit), nie myodoo."""
    from smartmyodoo.api_routers.workspaces import _resolve_odoo_creds

    creds = _resolve_odoo_creds(_vault_grfood_has_own(), "grfood")
    assert creds.get("url") == GRFOOD_URL


# ── T3 (V3): OdooClient — marker + FAIL LOUD zamiast ENV ──────────────────────


def test_t3_unconfigured_nondefault_raises_not_env(monkeypatch):
    """GREEN: grfood bez creds + ENV=myodoo → OdooClient("default") (jak wołają narzędzia)
    RZUCA OdooWorkspaceUnconfigured, NIE łączy z ENV. RED przed fixem: url = ENV/myodoo."""
    monkeypatch.setenv("ODOO_URL", MYODOO_URL)
    monkeypatch.setenv("ODOO_DB", "myodoo")
    monkeypatch.setenv("ODOO_USERNAME", "admin")
    monkeypatch.setenv("ODOO_PASSWORD", "pass")

    from smartmyodoo.api_routers.chat import _inject_odoo_creds

    _inject_odoo_creds(_vault_default_only_typed(), "grfood")
    with pytest.raises(OdooWorkspaceUnconfigured) as ei:
        OdooClient("default")  # narzędzia LLM budują klienta pod "default"
    assert ei.value.workspace_id == "grfood"


def test_t3_default_with_env_still_connects(monkeypatch):
    """Regres: ws=`default` bez creds w Skarbcu → ENV działa (tryb `vault run`)."""
    monkeypatch.setenv("ODOO_URL", MYODOO_URL)
    monkeypatch.setenv("ODOO_DB", "myodoo")
    monkeypatch.setenv("ODOO_USERNAME", "admin")
    monkeypatch.setenv("ODOO_PASSWORD", "pass")

    from smartmyodoo.api_routers.chat import _inject_odoo_creds

    _inject_odoo_creds({}, "default")  # default bez creds → brak markera
    c = OdooClient("default")
    assert c.url == MYODOO_URL and c.db == "myodoo"


def test_t3_nondefault_with_own_creds_connects(monkeypatch):
    """DoD live-recheck: po dodaniu klucza grfood czat łączy z gfit (nie myodoo)."""
    for k in ("ODOO_URL", "ODOO_DB", "ODOO_USERNAME", "ODOO_PASSWORD"):
        monkeypatch.delenv(k, raising=False)

    from smartmyodoo.api_routers.chat import _inject_odoo_creds

    _inject_odoo_creds(_vault_grfood_has_own(), "grfood")
    c = OdooClient("default")  # narzędzia wołają pod "default"; kontekst = grfood
    assert c.url == GRFOOD_URL and c.db == "gfitdb"


def test_t3_env_fallback_without_marker_regression(monkeypatch):
    """Regres istniejącego kontraktu: bez markera i bez creds → ENV (tak jak dotąd)."""
    monkeypatch.setenv("ODOO_URL", MYODOO_URL)
    monkeypatch.setenv("ODOO_DB", "myodoo")
    monkeypatch.setenv("ODOO_USERNAME", "admin")
    monkeypatch.setenv("ODOO_PASSWORD", "pass")
    set_odoo_creds(None)
    set_odoo_unconfigured(None)
    c = OdooClient("default")
    assert c.url == MYODOO_URL


# ── T4 (D4): sanityzowany komunikat użytkownikowi ─────────────────────────────


def test_t4_classify_error_is_clean_and_leakfree():
    """classify_odoo_error(OdooWorkspaceUnconfigured) → „❌…" z nazwą przestrzeni,
    BEZ URL/hasła/klucza (izolacja klienta, ART.2)."""
    from smartmyodoo.mcp.odoo_errors import classify_odoo_error

    out = classify_odoo_error(
        OdooWorkspaceUnconfigured("grfood"), workspace_id="default"
    )
    assert out.startswith("❌")
    assert "grfood" in out and "ODOO_DATA" in out
    assert MYODOO_URL not in out and GRFOOD_URL not in out
    assert "KEY-" not in out


def test_t4_executor_invoke_tool_sanitizes_unconfigured(monkeypatch):
    """Parytet D4 w executorze: narzędzie rzucające OdooWorkspaceUnconfigured →
    zwrot „❌…" (sukces=False), bez str(e)/sekretów; prefiks „❌" dla ERROR_REPORT_RULE."""
    from smartmyodoo.swarm import executor as ex_mod
    from smartmyodoo.swarm.executor import SkillExecutor

    def _boom(**kwargs):
        raise OdooWorkspaceUnconfigured("grfood")

    monkeypatch.setitem(
        ex_mod.TOOL_REGISTRY, "odoo_search", {"callable": _boom, "schema": {}}
    )
    ex = SkillExecutor(workspace_id="grfood")
    result, success, _ = ex._invoke_tool("odoo_search", {}, blocked=False, sandbox_activated=False)
    assert success is False
    assert result.startswith("❌")
    assert MYODOO_URL not in result and "KEY-" not in result


def test_t4_tool_path_returns_clean_error(monkeypatch):
    """Ścieżka realnego narzędzia czatu (search_odoo_records z mcp/server.py): grfood
    bez creds → {"error": „❌…"} bez sekretów, ZAMIAST danych z myodoo (cross-client guard)."""
    for k in ("ODOO_URL", "ODOO_DB", "ODOO_USERNAME", "ODOO_PASSWORD"):
        monkeypatch.setenv(k, "should-not-be-used")
    monkeypatch.setenv("PII_ENABLED_DEFAULT", "false")  # wyjątek pada przed PII

    from smartmyodoo.api_routers.chat import _inject_odoo_creds
    from smartmyodoo.mcp.server import search_odoo_records

    _inject_odoo_creds(_vault_default_only_typed(), "grfood")
    result = search_odoo_records("res.partner", workspace_id="default")
    assert isinstance(result, dict) and "error" in result
    assert result["error"].startswith("❌")
    assert MYODOO_URL not in result["error"]
    # nie zwrócono rekordów z cudzej instancji
    assert "records" not in result
