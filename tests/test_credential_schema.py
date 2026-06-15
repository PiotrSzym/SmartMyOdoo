"""K1 (KEY-01): typowany model Credential + walidacja per typ.

Dowód: konstrukcja niekompletnego poświadczenia danego typu PADA (ValidationError);
poprawne przechodzi. Rozpoznanie po `type`, nie po nazwie.
"""

import pytest
from pydantic import ValidationError

from smartmyodoo.vault.schemas import Credential, CredentialType


def test_llm_requires_provider_and_api_key():
    with pytest.raises(ValidationError):
        Credential(
            name="moj-klucz", type=CredentialType.LLM_PROVIDER
        )  # brak provider+api_key
    with pytest.raises(ValidationError):
        Credential(
            name="x", type=CredentialType.LLM_PROVIDER, provider="openrouter"
        )  # brak api_key


def test_llm_valid():
    c = Credential(
        name="dowolna nazwa",
        type=CredentialType.LLM_PROVIDER,
        provider="openrouter",
        api_key="sk-or-v1-xxx",
    )
    assert c.type == CredentialType.LLM_PROVIDER
    assert c.provider == "openrouter"
    assert c.workspace_id == "default"


def test_odoo_data_requires_connection_fields():
    with pytest.raises(ValidationError):
        Credential(
            name="acme", type=CredentialType.ODOO_DATA, url="https://x"
        )  # brak db, login


def test_odoo_data_and_timesheet_valid():
    data = Credential(
        name="ACME prod",
        type=CredentialType.ODOO_DATA,
        url="https://acme.odoo.com",
        db="acme-main",
        login="bot@acme.com",
        password="secret",
    )
    assert data.type == CredentialType.ODOO_DATA

    ts = Credential(
        name="Rozliczenia",
        type=CredentialType.ODOO_TIMESHEET,
        url="https://moja.odoo.com",
        db="moja-main",
        login="me@firma.pl",
        password="secret",
        default_project_ref="42",
    )
    assert ts.type == CredentialType.ODOO_TIMESHEET
    assert ts.default_project_ref == "42"
