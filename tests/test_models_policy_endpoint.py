"""K6 (KEY-01): testy endpointu /api/models/policy + utrwalania typowanych pól sekretu."""

import pytest
from fastapi.testclient import TestClient

from smartmyodoo.api import app

HEADERS = {"Authorization": "Bearer 1111"}


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def setup_vault_env(tmp_path):
    import smartmyodoo.vault.vault as vault

    vault.PIN_SALT_FILE = str(tmp_path / "pin_salt.cfg")
    vault.MASTER_SALT_FILE = str(tmp_path / "master_salt.cfg")
    vault.PIN_KEY_FILE = str(tmp_path / "pin_key.enc")
    vault.MASTER_KEY_FILE = str(tmp_path / "master_key.enc")
    vault.VAULT_DATA_FILE = str(tmp_path / "vault_data.enc")
    vault.init_vault_core("1111", "master")
    yield


def test_get_policy_returns_tiers_and_budget(client):
    res = client.get("/api/models/policy", headers=HEADERS)
    assert res.status_code == 200
    body = res.json()
    assert set(body["tiers"]) == {"cheap", "standard", "premium"}
    assert body["budget"]["max_budget_usd"] > 0
    assert "spent_usd" in body["budget"]
    assert body["default_tier"] in {"cheap", "standard", "premium"}


def test_get_policy_requires_auth(client):
    assert client.get("/api/models/policy").status_code == 401


def test_put_policy_overrides_tier_and_budget(client):
    res = client.put(
        "/api/models/policy",
        json={"tiers": {"cheap": "test/cheap-model"}, "max_budget_usd": 5.0},
        headers=HEADERS,
    )
    assert res.status_code == 200
    body = res.json()
    assert body["tiers"]["cheap"] == "test/cheap-model"
    assert body["budget"]["max_budget_usd"] == 5.0
    # nieznany tier jest ignorowany, nie wywala 422
    res2 = client.put(
        "/api/models/policy", json={"tiers": {"bogus": "x"}}, headers=HEADERS
    )
    assert res2.status_code == 200


def test_typed_secret_persists_type_and_provider(client):
    payload = {
        "password": "",
        "api_key": "sk-test",
        "type": "llm_provider",
        "provider": "openrouter",
    }
    res = client.post("/api/secrets/OPENROUTER_K6", json=payload, headers=HEADERS)
    assert res.status_code == 200
    data = client.get("/api/secrets", headers=HEADERS).json()
    assert data["OPENROUTER_K6"]["type"] == "llm_provider"
    assert data["OPENROUTER_K6"]["provider"] == "openrouter"
