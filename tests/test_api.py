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
