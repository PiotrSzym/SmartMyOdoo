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
    from smartmyodoo.core.database import SessionLocal
    from smartmyodoo.core.models import Proposal, Workspace

    db = SessionLocal()
    db.query(Proposal).delete()
    db.query(Workspace).delete()
    db.commit()
    db.close()
    yield
    db = SessionLocal()
    db.query(Proposal).delete()
    db.query(Workspace).delete()
    db.commit()
    db.close()


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
    from smartmyodoo.core.database import SessionLocal
    from smartmyodoo.core.models import Proposal

    p_id = data["proposal_data"]["proposal_id"]
    db = SessionLocal()
    db_prop = db.query(Proposal).filter(Proposal.id == p_id).first()
    assert db_prop.workspace_id == "staging"
    db.close()


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
    client.post(
        "/api/workspaces",
        json={"id": "default", "name": "Pierwszy"},
        headers=auth_headers,
    )
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
    res = client.put("/api/workspaces/x", json={"name": "y"})
    assert res.status_code == 401


# ── UX-03: Workspace Onboarding with Vault ────────────────────────────────────


def test_workspace_onboarding_no_creds_still_works(client, auth_headers):
    """POST /api/workspaces bez poświadczeń działa normalnie"""
    res = client.post(
        "/api/workspaces",
        json={"id": "nocreds", "name": "No Creds", "odoo_url": "http://test"},
        headers=auth_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["vault_saved"] is False


def test_workspace_onboarding_creates_vault_secret(client, auth_headers):
    """POST /api/workspaces z poświadczeniami tworzy wpis w Vault"""
    res = client.post(
        "/api/workspaces",
        json={
            "id": "withcreds",
            "name": "With Creds",
            "odoo_url": "http://withcreds",
            "admin_login": "admin",
            "admin_password": "supersecretpassword",
            "admin_api_key": "myapikey",
            "admin_expires": "2030-01-01",
        },
        headers=auth_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["vault_saved"] is True

    # Verify in vault
    vault_res = client.get("/api/secrets", headers=auth_headers)
    assert vault_res.status_code == 200
    secrets = vault_res.json()
    assert "withcreds_ODOO" in secrets
    assert secrets["withcreds_ODOO"]["login"] == "admin"
    assert secrets["withcreds_ODOO"]["workspace_id"] == "withcreds"


def test_workspace_settings_hides_credentials(client, auth_headers):
    """GET /api/workspaces nie zwraca poświadczeń, tylko metadane"""
    res = client.get("/api/workspaces", headers=auth_headers)
    assert res.status_code == 200
    wks = res.json()
    for w in wks:
        assert "admin_password" not in w
        assert "password" not in w


# ── UX-04: Workspace Management Tests ──────────────────────────────


def test_workspace_delete_no_cascade(client, auth_headers):
    """DELETE /api/workspaces/{id} bez kaskady Vault"""
    # Create
    client.post(
        "/api/workspaces",
        json={
            "id": "to-delete",
            "name": "ToDelete",
            "odoo_url": "http://td",
            "admin_login": "admin",
            "admin_password": "secret123",
        },
        headers=auth_headers,
    )
    # Delete without cascade
    res = client.delete(
        "/api/workspaces/to-delete?cascade_vault=false", headers=auth_headers
    )
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["secrets_removed"] == 0

    # Verify workspace is gone
    wks = client.get("/api/workspaces", headers=auth_headers).json()
    ws_ids = [w["id"] for w in wks]
    assert "to-delete" not in ws_ids

    # Secret should still exist
    secrets = client.get("/api/secrets", headers=auth_headers).json()
    assert "to-delete_ODOO" in secrets


def test_workspace_delete_reparents_secrets_to_default(client, auth_headers):
    """Orphan-guard: usunięcie przestrzeni bez kaskady PRZEPINA jej sekrety na
    `default` (zamiast zostawiać wiszące, niewidoczne rekordy)."""
    client.post(
        "/api/workspaces",
        json={
            "id": "orphan-src",
            "name": "OrphanSrc",
            "odoo_url": "http://os",
            "admin_login": "admin",
            "admin_password": "secret789",
        },
        headers=auth_headers,
    )
    # Sekret startuje przypięty do orphan-src
    before = client.get(
        "/api/secrets?workspace_id=orphan-src", headers=auth_headers
    ).json()
    assert "orphan-src_ODOO" in before

    res = client.delete(
        "/api/workspaces/orphan-src?cascade_vault=false", headers=auth_headers
    )
    assert res.status_code == 200
    data = res.json()
    assert data["secrets_removed"] == 0
    assert data["secrets_reassigned"] >= 1

    # Brak sierot: nic nie zostało na nieistniejącej przestrzeni...
    orphaned = client.get(
        "/api/secrets?workspace_id=orphan-src", headers=auth_headers
    ).json()
    assert "orphan-src_ODOO" not in orphaned
    # ...a sekret jest teraz widoczny w `default`.
    in_default = client.get(
        "/api/secrets?workspace_id=default", headers=auth_headers
    ).json()
    assert "orphan-src_ODOO" in in_default


def test_workspace_delete_with_cascade(client, auth_headers):
    """DELETE /api/workspaces/{id}?cascade_vault=true soft-deletuje sekrety"""
    # Create
    client.post(
        "/api/workspaces",
        json={
            "id": "cascade-del",
            "name": "CascadeDel",
            "odoo_url": "http://cd",
            "admin_login": "admin",
            "admin_password": "secret456",
        },
        headers=auth_headers,
    )
    # Delete with cascade
    res = client.delete(
        "/api/workspaces/cascade-del?cascade_vault=true", headers=auth_headers
    )
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["secrets_removed"] >= 1

    # Secret should have deleted_at
    all_secrets = client.get("/api/secrets", headers=auth_headers).json()
    if "cascade-del_ODOO" in all_secrets:
        assert "deleted_at" in all_secrets["cascade-del_ODOO"]


def test_workspace_reorder(client, auth_headers):
    """PUT /api/workspaces/reorder zmienia position"""
    # Ensure we have defaults
    wks = client.get("/api/workspaces", headers=auth_headers).json()
    ws_ids = [w["id"] for w in wks]

    if len(ws_ids) >= 2:
        # Reverse order
        reversed_order = list(reversed(ws_ids))
        res = client.put(
            "/api/workspaces/reorder",
            json={"order": reversed_order},
            headers=auth_headers,
        )
        assert res.status_code == 200

        # Verify order persists
        wks2 = client.get("/api/workspaces", headers=auth_headers).json()
        new_ids = [w["id"] for w in wks2]
        assert new_ids == reversed_order


def test_delete_secrets_by_workspace(client, auth_headers):
    """DELETE /api/secrets/by-workspace/{ws_id} soft-deletuje powiązane sekrety"""
    # Create workspace with secret
    client.post(
        "/api/workspaces",
        json={
            "id": "sec-del",
            "name": "SecDel",
            "odoo_url": "http://sd",
            "admin_login": "admin",
            "admin_password": "pass789",
        },
        headers=auth_headers,
    )
    # Delete secrets only
    res = client.delete("/api/secrets/by-workspace/sec-del", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["secrets_removed"] >= 1

    # Workspace should still exist
    wks = client.get("/api/workspaces", headers=auth_headers).json()
    ws_ids = [w["id"] for w in wks]
    assert "sec-del" in ws_ids


def test_delete_nonexistent_workspace(client, auth_headers):
    """DELETE /api/workspaces/{id} zwraca 404 na nieistniejący workspace"""
    res = client.delete("/api/workspaces/nonexistent-ws-xyz", headers=auth_headers)
    assert res.status_code == 404


def test_api_pipeline_run(client, auth_headers, mocker):
    mock_pipeline = mocker.patch("smartmyodoo.swarm.pipeline.ExecutionPipeline")
    mock_instance = mock_pipeline.return_value
    mock_instance.state.name = "SYNC"
    mock_instance.adp_plan = {"mocked": "plan"}
    mock_instance._rolled_back = False

    res = client.post(
        "/api/pipeline/run",
        json={
            "message": "uruchom pipeline",
            "workspace_id": "test_ws",
            "session_id": "test_sess",
        },
        headers=auth_headers,
    )

    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["final_state"] == "SYNC"
    assert data["rolled_back"] is False


def test_api_pipeline_run_rollback(client, auth_headers, mocker):
    mock_pipeline = mocker.patch("smartmyodoo.swarm.pipeline.ExecutionPipeline")
    mock_instance = mock_pipeline.return_value
    mock_instance.state.name = "SYNC"
    mock_instance.adp_plan = {}
    mock_instance._rolled_back = True

    res = client.post(
        "/api/pipeline/run",
        json={
            "message": "zrob cos zlego",
            "workspace_id": "test_ws",
            "session_id": "test_sess",
        },
        headers=auth_headers,
    )

    assert res.status_code == 200
    data = res.json()
    assert data["success"] is False
    assert data["rolled_back"] is True


# ── SH-LOG-01: parser wklejanych logów Odoo.sh (endpoint) ──────────────────


def test_logs_parse_endpoint(client, auth_headers):
    """POST /api/logs/parse zwraca strukturę z root cause bottom-up i HTTP 500."""
    log = (
        '2024-01-15 14:00:23,456 12345 INFO db werkzeug: 1.2.3.4 - - '
        '[15/Jan/2024 14:00:23] "POST /web/dataset/call_kw HTTP/1.1" 500 -\n'
        "2024-01-15 14:00:23,460 12345 ERROR db odoo.http: Exception.\n"
        "Traceback (most recent call last):\n"
        '  File "x.py", line 1, in f\n'
        "odoo.exceptions.ValidationError: Pole wymagane\n"
    )
    res = client.post("/api/logs/parse", json={"text": log}, headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    s = data["summary"]
    assert s["by_level"]["ERROR"] == 1
    assert s["http_errors"][0]["status"] == 500
    assert s["root_causes"] == ["odoo.exceptions.ValidationError: Pole wymagane"]


def test_logs_parse_requires_auth(client):
    """Bez Bearer endpoint odrzuca — log może zawierać dane wrażliwe."""
    res = client.post("/api/logs/parse", json={"text": "x"})
    assert res.status_code in (401, 403)
