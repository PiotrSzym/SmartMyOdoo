import os
import pytest
from sqlalchemy import text
from smartmyodoo.core.database import Base, engine, SessionLocal, DB_PATH
from smartmyodoo.core.models import Proposal, TokenUsage


@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
    # Zabezpieczamy, że testy pracują na bazie testowej
    assert (
        "test" in DB_PATH
        or DB_PATH == "sqlite:///:memory:"
        or "test" in os.environ.get("DATABASE_URL", "")
    ), "Tests should run on a test database!"

    # Tworzymy tabele
    Base.metadata.create_all(bind=engine)
    yield
    # Sprzątamy
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_database_pragma_wal(db_session):
    if DB_PATH.startswith("sqlite"):
        if ":memory:" in DB_PATH:
            pytest.skip("In-memory SQLite doesn't support WAL")
        result = db_session.execute(text("PRAGMA journal_mode")).scalar()
        assert result.lower() == "wal"


def test_database_pragma_foreign_keys(db_session):
    if DB_PATH.startswith("sqlite"):
        result = db_session.execute(text("PRAGMA foreign_keys")).scalar()
        assert int(result) == 1


def test_crud_proposals(db_session):
    # Create
    new_proposal = Proposal(id="test_id", status="draft", values='{"task": "test"}')
    db_session.add(new_proposal)
    db_session.commit()
    db_session.refresh(new_proposal)

    assert new_proposal.id is not None
    assert new_proposal.status == "draft"

    # Read
    fetched = db_session.query(Proposal).filter(Proposal.id == new_proposal.id).first()
    assert fetched is not None
    assert fetched.values == '{"task": "test"}'

    # Update
    fetched.status = "approved"
    db_session.commit()

    fetched_updated = (
        db_session.query(Proposal).filter(Proposal.id == new_proposal.id).first()
    )
    assert fetched_updated.status == "approved"

    # Delete
    db_session.delete(fetched_updated)
    db_session.commit()

    deleted = db_session.query(Proposal).filter(Proposal.id == new_proposal.id).first()
    assert deleted is None


def test_token_usage_insert(db_session):
    usage = TokenUsage(model="gpt-4", tokens_used=150, cost=0.003)
    db_session.add(usage)
    db_session.commit()

    fetched = db_session.query(TokenUsage).filter(TokenUsage.model == "gpt-4").first()
    assert fetched is not None
    assert fetched.tokens_used == 150
    assert fetched.cost == 0.003
