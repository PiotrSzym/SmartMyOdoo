"""FIX-04 T4 (A-4): handler WS nie wysyła treści wyjątku (ADR-011 parytet REST/WS).

Wymuszony wyjątek z „sekretem" w komunikacie → payload WS zawiera TYLKO nazwę typu
(f"Błąd agenta: {type(e).__name__}"); pełna treść zostaje w logu serwera.
"""

import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from smartmyodoo.api import app
from smartmyodoo.core.database import get_db, Base

_SECRET = "SEKRET-PIN-1111-DO-NOT-LEAK-9999"


@pytest.fixture
def client(tmp_path):
    """Izolowana baza z tabelami — odporna na kolejność kolekcji (inny test robi
    drop_all na wspólnym engine; bez własnej bazy audit-insert WS pada na
    'no such table: audit_log' ZANIM zadziała zmockowany wyjątek)."""
    engine = create_engine(
        f"sqlite:///{tmp_path / 'ws_err.db'}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def _override_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override_db
    yield TestClient(app)
    app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_ws_error_payload_hides_exception_content(client):
    with patch("smartmyodoo.api_routers.chat.get_auth_key") as mock_auth, patch(
        "smartmyodoo.api_routers.chat.vault.load_vault"
    ) as mock_vault, patch.dict(
        "os.environ", {"OPENROUTER_KEY": "test_llm_key"}
    ), patch(
        "smartmyodoo.swarm.executor.SkillExecutor.execute_stream"
    ) as mock_exec:
        mock_auth.return_value = (b"testkey", "admin")
        mock_vault.return_value = {"OPENROUTER_KEY": {"api_key": "test_llm_key"}}

        # Generator, który wybucha wyjątkiem NIOSĄCYM „sekret" w treści.
        async def boom(*args, **kwargs):
            raise RuntimeError(_SECRET)
            yield  # czyni funkcję async-generatorem (spójne z kontraktem execute_stream)

        mock_exec.side_effect = boom

        with client.websocket_connect("/api/chat/stream") as websocket:
            websocket.send_json({"message": "Hello", "password": "goodpassword"})
            data = websocket.receive_json()

            assert data["type"] == "error"
            # sekret NIE może przeciec do klienta
            assert _SECRET not in data["content"]
            # payload zawiera TYLKO nazwę typu wyjątku
            assert data["content"] == "Błąd agenta: RuntimeError"
