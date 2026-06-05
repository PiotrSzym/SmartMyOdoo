import logging
import pytest

try:
    from smartmyodoo.core.log_config import SecretFilter, setup_logging
except ImportError:
    SecretFilter = None  # type: ignore
    setup_logging = None  # type: ignore


def test_secret_filter_redacts_sensitive_info():
    """
    Sprawdza, czy SecretFilter zamienia wrażliwe stringi na [REDACTED].
    """
    if SecretFilter is None:
        pytest.fail("SecretFilter is not yet implemented")

    filter_instance = SecretFilter()

    # Tworzymy symulowany log record
    record1 = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="Connecting to API with token sk-or-v1-abc123def456 and password=secret",
        args=(),
        exc_info=None,
    )

    # Wywołanie filtru modyfikuje record w miejscu
    filter_instance.filter(record1)

    assert "sk-or-v1" not in record1.getMessage()
    assert "password=secret" not in record1.getMessage()
    assert "[REDACTED]" in record1.getMessage()


def test_secret_filter_bearer_token():
    if SecretFilter is None:
        pytest.fail("SecretFilter is not yet implemented")

    filter_instance = SecretFilter()
    record = logging.LogRecord(
        name="test",
        level=logging.DEBUG,
        pathname="",
        lineno=0,
        msg="Header: Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5c",
        args=(),
        exc_info=None,
    )

    filter_instance.filter(record)
    assert "eyJhbGciOiJI" not in record.getMessage()
    assert "[REDACTED]" in record.getMessage()


def test_global_exception_handler_returns_json():
    """
    Sprawdza, czy uruchomienie endpointu, który rzuca wyjątek,
    nie zwraca stacktrace'a do klienta (Security: ADR-011).
    """
    try:
        from fastapi.testclient import TestClient
        from smartmyodoo.main import app
    except ImportError:
        pytest.fail("FastAPI app is not properly configured yet")

    # Tworzymy ukryty endpoint testowy symulujący krytyczny błąd
    @app.get("/_test_crash")
    def crash():
        raise RuntimeError(
            "This is a secret internal error with db credentials: password=dbpass"
        )

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/_test_crash")

    # Zgodnie z ADR-011 błąd 500 ma zwracać JSON z generyczną wiadomością
    assert response.status_code == 500
    data = response.json()
    assert "password=dbpass" not in str(data)
    assert data.get("detail") == "Internal Server Error"
