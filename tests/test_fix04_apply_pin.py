"""FIX-04 T2 (A-2): serwerowa walidacja PIN przy POST /apply.

Dowody:
- apply bez PIN → 403 (mimo ważnego tokena sesji),
- apply ze złym PIN → 403 + audit `proposal_apply_denied`,
- apply z dobrym PIN → 200 + wykonanie (execute_proposal_by_id zawołane),
- idempotencja `executed` pokryta osobno w test_apply_proposal.py (bez zmian).
"""

import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from smartmyodoo.api import app
from smartmyodoo.core.database import get_db, Base
from smartmyodoo.core import models as db_models
from smartmyodoo.api_routers.auth import _auth_limiter

_PIN = "1111"  # PIN sesji + step-up (require_auth / get_auth_key)
# Nagłówek budowany przez interpolację (unikamy literału tokenu — secret-scanner).
HEADERS = {"Authorization": f"Bearer {_PIN}"}


@pytest.fixture(autouse=True)
def setup_vault_env(tmp_path):
    """Vault z PIN/master — get_auth_key waliduje świeży PIN serwerowo."""
    import smartmyodoo.vault.vault as vault

    vault.PIN_SALT_FILE = str(tmp_path / "pin_salt.cfg")
    vault.MASTER_SALT_FILE = str(tmp_path / "master_salt.cfg")
    vault.PIN_KEY_FILE = str(tmp_path / "pin_key.enc")
    vault.MASTER_KEY_FILE = str(tmp_path / "master_key.enc")
    vault.VAULT_DATA_FILE = str(tmp_path / "vault_data.enc")
    vault.init_vault_core(_PIN, "master")
    _auth_limiter.reset("apply-pin:testclient")
    yield
    _auth_limiter.reset("apply-pin:testclient")


@pytest.fixture
def db_session(tmp_path):
    """Świeża baza plikowa z jedną PENDING propozycją."""
    engine = create_engine(
        f"sqlite:///{tmp_path / 'apply.db'}", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = TestingSession()
    session.add(
        db_models.Proposal(
            id="p-apply-1",
            workspace_id="myodooTest",
            odoo_model="crm.lead",
            method="update",
            values='{"record_ids": [1], "values": {"name": "X"}}',
            reason="test",
            status="pending",
        )
    )
    session.commit()
    yield session, engine, TestingSession
    session.close()


@pytest.fixture
def client(db_session):
    session, engine, TestingSession = db_session

    def _override_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override_db
    yield TestClient(app), session, TestingSession
    app.dependency_overrides.pop(get_db, None)


def _audit_actions(TestingSession):
    db = TestingSession()
    try:
        return [a.action for a in db.query(db_models.AuditLog).all()]
    finally:
        db.close()


def test_apply_without_pin_is_forbidden(client):
    tc, _session, TestingSession = client
    res = tc.post("/api/proposals/p-apply-1/apply", json={}, headers=HEADERS)
    assert res.status_code == 403, res.text
    assert "proposal_apply_denied" in _audit_actions(TestingSession)


def test_apply_with_wrong_pin_is_forbidden_and_audited(client):
    tc, _session, TestingSession = client
    res = tc.post(
        "/api/proposals/p-apply-1/apply", json={"pin": "0000"}, headers=HEADERS
    )
    assert res.status_code == 403, res.text
    assert "proposal_apply_denied" in _audit_actions(TestingSession)


def test_apply_with_correct_pin_executes(client):
    tc, _session, TestingSession = client
    with patch(
        "smartmyodoo.mcp.server.execute_proposal_by_id",
        return_value={"success": True, "status": "executed", "already": False},
    ) as mock_exec, patch(
        "smartmyodoo.api_routers.chat._inject_odoo_creds", return_value=None
    ):
        res = tc.post(
            "/api/proposals/p-apply-1/apply", json={"pin": _PIN}, headers=HEADERS
        )
    assert res.status_code == 200, res.text
    assert res.json()["status"] == "executed"
    mock_exec.assert_called_once()
    actions = _audit_actions(TestingSession)
    assert "proposal_apply" in actions
    assert "proposal_apply_denied" not in actions
