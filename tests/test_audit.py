import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from smartmyodoo.core.models import Base, AuditLog
from smartmyodoo.core.audit import log_tool_call


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_log_tool_call(db_session):
    log_tool_call(
        db_session,
        workspace_id="ws_1",
        tool_name="odoo_create",
        args={"name": "test"},
        result="Success",
        success=True,
    )

    logs = db_session.query(AuditLog).all()
    assert len(logs) == 1
    assert logs[0].action == "TOOL:odoo_create:OK"
    assert "test" in logs[0].details


def test_audit_sanitization(db_session):
    log_tool_call(
        db_session,
        workspace_id="ws_1",
        tool_name="test_tool",
        args={"password": "secret_password", "normal": "data"},
        result="Success",
        success=True,
    )

    logs = db_session.query(AuditLog).all()
    assert len(logs) == 1
    assert "secret_password" not in logs[0].details
    assert "***REDACTED***" in logs[0].details
    assert "data" in logs[0].details
