import logging
import re


class SecretFilter(logging.Filter):
    """
    Filtr logów implementujący politykę Zero Trust (ADR-011).
    Wyszukuje wzorce wrażliwe i zamienia je na [REDACTED].
    """

    def __init__(self, name=""):
        super().__init__(name)
        # Deny list wzorców
        self.patterns = [
            re.compile(r"sk-or-[a-zA-Z0-9\-_]+"),  # OpenRouter / OpenAI API keys
            re.compile(r"password=[^\s&]+"),  # Password w querystring / logach
            re.compile(r"Bearer\s+[a-zA-Z0-9\-\._~+/]+=*"),  # Bearer tokens (JWT itp)
        ]

    def filter(self, record):
        if not isinstance(record.msg, str):
            try:
                record.msg = str(record.msg)
            except Exception:
                pass

        if isinstance(record.msg, str):
            for pattern in self.patterns:
                record.msg = pattern.sub("[REDACTED]", record.msg)

        return True


def setup_logging():
    """
    Konfiguruje globalnego loggera dodając SecretFilter.
    Wywoływane przy starcie aplikacji.
    """
    root_logger = logging.getLogger()

    # Dodajemy filtr do istniejących handlerów
    for handler in root_logger.handlers:
        handler.addFilter(SecretFilter())

    # Upewniamy się, że logger FastAPI też używa filtra
    fastapi_logger = logging.getLogger("fastapi")
    for handler in fastapi_logger.handlers:
        handler.addFilter(SecretFilter())

    uvicorn_logger = logging.getLogger("uvicorn")
    for handler in uvicorn_logger.handlers:
        handler.addFilter(SecretFilter())

    # Globalne dodanie na roocie w razie nowych handlerów
    root_logger.addFilter(SecretFilter())
