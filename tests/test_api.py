import pytest
from fastapi.testclient import TestClient

# Przygotowujemy mocki lub setupy na wypadek, gdyby FastAPI server jeszcze nie istniał
try:
    from smartmyodoo.api import app

    assert app is not None
    assert app.title == "SmartMyVault API"

except ImportError:
    app = None  # type: ignore


# Jeśli aplikacja nie istnieje, TestClient rzuci błędem, dlatego w fazie RED musimy to obsłużyć.
@pytest.fixture
def client():
    if app is None:
        pytest.fail("FastAPI app is not implemented yet in api.py")
    return TestClient(app)


@pytest.fixture(autouse=True)
def setup_vault_env(tmp_path):
    # Nadpisujemy ścieżki vaulta dla środowiska testowego
    import smartmyodoo.vault.vault as vault

    vault.PIN_SALT_FILE = str(tmp_path / "test_api_pin_salt.cfg")
    vault.MASTER_SALT_FILE = str(tmp_path / "test_api_master_salt.cfg")
    vault.PIN_KEY_FILE = str(tmp_path / "test_api_pin_key.enc")
    vault.MASTER_KEY_FILE = str(tmp_path / "test_api_master_key.enc")
    vault.VAULT_DATA_FILE = str(tmp_path / "test_api_vault_data.enc")

    vault.init_vault_core("1111", "master")
    yield


def test_api_status(client):
    res = client.get("/api/status")
    assert res.status_code == 200
    assert res.json()["initialized"] is True


def test_api_auth(client):
    res = client.post("/api/auth", json={"password": "1111"})
    assert res.status_code == 200
    assert res.json()["role"] == "user"

    res_admin = client.post("/api/auth", json={"password": "master"})
    assert res_admin.status_code == 200
    assert res_admin.json()["role"] == "admin"

    res_invalid = client.post("/api/auth", json={"password": "bad"})
    assert res_invalid.status_code == 401


def test_api_crud_operations(client):
    headers = {"Authorization": "Bearer 1111"}

    # 1. CREATE
    res = client.post(
        "/api/secrets/TEST_CRUD_API",
        json={"password": "api_test_password"},
        headers=headers,
    )
    assert res.status_code == 200
    assert res.json()["success"] is True

    # 2. READ
    res = client.get("/api/secrets", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "TEST_CRUD_API" in data
    assert data["TEST_CRUD_API"]["password"] == "api_test_password"

    # 3. SOFT DELETE
    res = client.delete("/api/secrets/TEST_CRUD_API", headers=headers)
    assert res.status_code == 200
    assert res.json()["success"] is True

    # 4. READ (soft deleted)
    res = client.get("/api/secrets", headers=headers)
    data = res.json()
    assert "TEST_CRUD_API" in data
    assert "deleted_at" in data["TEST_CRUD_API"]

    # 5. RESTORE
    res = client.post("/api/secrets/TEST_CRUD_API/restore", headers=headers)
    assert res.status_code == 200
    assert res.json()["success"] is True

    # 6. READ (restored)
    res = client.get("/api/secrets", headers=headers)
    data = res.json()
    assert "deleted_at" not in data["TEST_CRUD_API"]

    # 7. PERMANENT DELETE
    res = client.delete("/api/secrets/TEST_CRUD_API/permanent", headers=headers)
    assert res.status_code == 200
    assert res.json()["success"] is True

    # 8. READ (permanent deletion verified)
    res = client.get("/api/secrets", headers=headers)
    assert "TEST_CRUD_API" not in res.json()


def test_api_change_pin_non_admin(client):
    res = client.post(
        "/api/change-pin",
        json={"new_pin": "2222"},
        headers={"Authorization": "Bearer 1111"},
    )
    assert res.status_code == 403
    assert "Admin role required" in res.json()["detail"]


def test_api_change_pin_admin(client):
    res = client.post(
        "/api/change-pin",
        json={"new_pin": "2222"},
        headers={"Authorization": "Bearer master"},
    )
    assert res.status_code == 200
    assert res.json()["success"] is True


def test_api_init_already_initialized(client):
    res = client.post("/api/init", json={"pin": "1234", "master": "admin123"})
    assert res.status_code == 400
    assert "Already initialized" in res.json()["detail"]


def test_api_init_missing_data(client, mocker):
    mocker.patch("os.path.exists", return_value=False)

    # Przechodzimy walidację pydantic w FastAPI
    res = client.post("/api/init", json={"pin": "12"})
    assert res.status_code == 422  # Pydantic ValidationError

    res2 = client.post("/api/init", json={"pin": "123", "master": "admin"})
    assert res2.status_code == 422  # Pydantic ValidationError


@pytest.fixture
def auth_headers():
    return {"Authorization": "Bearer 1111"}


# ── HUB-S2: Testy integracji Chat ↔ Dispatcher ─────────────────────────────


def test_chat_classifies_code_intent(client, auth_headers):
    """POST /api/chat z wiadomością kodową → category=A, persona=Developer"""
    res = client.post(
        "/api/chat",
        json={
            "message": "napisz mi kod logowania",
            "user_id": 1,
            "session_id": "test-s1",
        },
        headers=auth_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["category"] == "A"
    assert data["persona"] == "Developer"
    assert data["model"] is not None
    assert data["action_type"] == "CHAT"


def test_chat_classifies_db_intent(client, auth_headers):
    """POST /api/chat z wiadomością bazodanową → category=B, persona=DBA"""
    res = client.post(
        "/api/chat",
        json={
            "message": "pokaż tabelę klientów",
            "user_id": 1,
            "session_id": "test-s2",
        },
        headers=auth_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["category"] == "B"
    assert data["persona"] == "Database Administrator"


def test_chat_classifies_general_intent(client, auth_headers):
    """POST /api/chat z ogólną wiadomością → category=H, persona=Generic Assistant"""
    res = client.post(
        "/api/chat",
        json={"message": "cześć co słychać", "user_id": 1, "session_id": "test-s3"},
        headers=auth_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["category"] == "H"
    assert data["persona"] == "Generic Assistant"
    assert "reply" in data


# ── HUB-S3: Testy Proposals + Workspace ─────────────────────────────────────


@pytest.fixture(autouse=True)
def reset_stores():
    """Czyści in-memory stores przed każdym testem S3"""
    import smartmyodoo.api as api_module

    api_module._proposals.clear()
    yield
    api_module._proposals.clear()


def test_chat_generates_shadow_proposal(client, auth_headers):
    """POST /api/chat z intencją DBA → generuje propozycję Shadow Mode"""
    res = client.post(
        "/api/chat",
        json={
            "message": "zrób migrację tabeli partnerów",
            "user_id": 1,
            "session_id": "test-s4",
            "workspace_id": "staging",
        },
        headers=auth_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["action_type"] == "SHADOW_PROPOSAL"
    assert data["category"] == "B"
    assert data["proposal_data"] is not None
    assert data["proposal_data"]["proposal_id"] is not None
    assert data["proposal_data"]["model"] == "res.partner"
    assert data["proposal_data"]["method"] == "CREATE"

    # Sprawdzamy czy backend właściwie podpiął workspace
    import smartmyodoo.api as api_module

    p_id = data["proposal_data"]["proposal_id"]
    assert api_module._proposals[p_id].workspace_id == "staging"


def test_proposals_crud(client, auth_headers):
    """Pełny flow: chat generuje propozycję → GET lista → approve → sprawdź status"""
    # 1. Generuj propozycję przez czat
    res = client.post(
        "/api/chat",
        json={
            "message": "pokaż bazę danych partnerów",
            "user_id": 1,
            "session_id": "test-p1",
        },
        headers=auth_headers,
    )
    proposal_id = res.json()["proposal_data"]["proposal_id"]

    # 2. GET lista propozycji
    res = client.get("/api/proposals", headers=auth_headers)
    assert res.status_code == 200
    proposals = res.json()
    assert len(proposals) == 1
    assert proposals[0]["id"] == proposal_id
    assert proposals[0]["status"] == "pending"

    # 3. Approve
    res = client.post(f"/api/proposals/{proposal_id}/approve", headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["status"] == "approved"

    # 4. Sprawdź status po approve
    res = client.get("/api/proposals", headers=auth_headers)
    assert res.json()[0]["status"] == "approved"


def test_proposal_reject(client, auth_headers):
    """Reject propozycji"""
    res = client.post(
        "/api/chat",
        json={
            "message": "zrób SQL na tabeli kontaktów",
            "user_id": 1,
            "session_id": "test-p2",
        },
        headers=auth_headers,
    )
    proposal_id = res.json()["proposal_data"]["proposal_id"]

    res = client.post(f"/api/proposals/{proposal_id}/reject", headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["status"] == "rejected"


def test_proposal_not_found(client, auth_headers):
    """404 dla nieistniejącej propozycji"""
    res = client.post("/api/proposals/nonexistent/approve", headers=auth_headers)
    assert res.status_code == 404


def test_workspaces_list(client, auth_headers):
    """GET /api/workspaces → domyślna lista 3 przestrzeni"""
    res = client.get("/api/workspaces", headers=auth_headers)
    assert res.status_code == 200
    workspaces = res.json()
    assert len(workspaces) >= 3
    ids = [w["id"] for w in workspaces]
    assert "default" in ids
    assert "dev" in ids
    assert "prod" in ids


def test_workspace_create(client, auth_headers):
    """POST /api/workspaces → nowa przestrzeń"""
    res = client.post(
        "/api/workspaces",
        json={
            "id": "staging",
            "name": "Staging Env",
            "odoo_url": "http://localhost:8069",
        },
        headers=auth_headers,
    )
    assert res.status_code == 200
    assert res.json()["id"] == "staging"

    # Sprawdź czy jest na liście
    res = client.get("/api/workspaces", headers=auth_headers)
    ids = [w["id"] for w in res.json()]
    assert "staging" in ids


def test_workspace_duplicate(client, auth_headers):
    """POST /api/workspaces z istniejącym ID → 400"""
    res = client.post(
        "/api/workspaces",
        json={"id": "default", "name": "Duplikat"},
        headers=auth_headers,
    )
    assert res.status_code == 400
    assert "already exists" in res.json()["detail"]


# ── HUB-S3: Regresja Security (Brak autoryzacji) ──────────────────────────────


def test_chat_requires_auth(client):
    res = client.post(
        "/api/chat", json={"message": "test", "user_id": 1, "session_id": "1"}
    )
    assert res.status_code == 401


def test_proposals_requires_auth(client):
    res = client.get("/api/proposals")
    assert res.status_code == 401
    res = client.post("/api/proposals/123/approve")
    assert res.status_code == 401


def test_workspaces_requires_auth(client):
    res = client.get("/api/workspaces")
    assert res.status_code == 401
    res = client.post("/api/workspaces", json={"id": "x", "name": "x"})
    assert res.status_code == 401
