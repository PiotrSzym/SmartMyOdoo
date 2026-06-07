import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from smartmyodoo.core.models import Base
from smartmyodoo.core.chat_repository import ChatRepository


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_save_message(db_session):
    repo = ChatRepository(db_session)
    repo.save_message("ws_1", "sess_1", "user", "Hello world")

    msgs = repo.get_session_messages("sess_1")
    assert len(msgs) == 1
    assert msgs[0]["role"] == "user"
    assert msgs[0]["content"] == "Hello world"


def test_smart_context(db_session):
    repo = ChatRepository(db_session)
    repo.save_message("ws_1", "sess_1", "user", "How to install Odoo?")
    repo.save_message("ws_1", "sess_1", "assistant", "Use apt-get.")
    repo.save_message("ws_1", "sess_2", "user", "What about db?")

    context = repo.get_smart_context("ws_1", "sess_2")
    assert len(context) == 1
    assert "sess_1" in context[0]["content"]
    assert "How to install Odoo?" in context[0]["content"]
