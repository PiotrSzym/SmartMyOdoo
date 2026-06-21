"""Status backendów współdzielonego stanu (Redis vs proces-lokalny) + log na starcie.

rate-limit (core/ratelimit), cache LLM (core/llm_cache), distributed lock (core/lock)
i kolejka (core/queue) działają poprawnie między procesami TYLKO z Redisem. Bez `REDIS_URL`
(lub gdy Redis nieosiągalny) degradują do trybu proces-lokalnego — OK dla 1 procesu, ale
przy wielu workerach limity liczą się per-worker, a lock nie chroni między procesami.

`log_backend_modes()` woła się na starcie aplikacji i jasno mówi, w jakim trybie działamy.
"""

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


def redis_reachable(url: Optional[str], timeout: float = 0.5) -> bool:
    """True gdy `url` ustawiony i Redis odpowiada na PING (krótki timeout)."""
    if not url:
        return False
    try:
        import redis  # type: ignore[import-untyped]

        client = redis.Redis.from_url(
            url, socket_connect_timeout=timeout, socket_timeout=timeout
        )
        client.ping()
        return True
    except Exception as e:  # noqa: BLE001
        logger.debug(f"[runtime] Redis ping nieudany: {e}")
        return False


def get_app_version() -> str:
    """RELEASE-01 T5: wersja wydania z metadanych pakietu (SSoT = pyproject.toml, D4).

    Preferuje `importlib.metadata.version('smartmyodoo')` (działa dla zainstalowanego
    pakietu — np. obraz Docker). Fallback: odczyt `version` wprost z pyproject.toml
    (środowisko dev z editable/uninstalled pakietem). Ostateczny fallback: "0.0.0".
    """
    from importlib import metadata

    try:
        return metadata.version("smartmyodoo")
    except metadata.PackageNotFoundError:
        pass

    # Fallback dev: pyproject.toml leży 3 poziomy nad tym plikiem
    # (smartmyodoo/core/runtime_info.py -> repo root).
    try:
        import tomllib

        root = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        with open(os.path.join(root, "pyproject.toml"), "rb") as fh:
            return str(tomllib.load(fh)["project"]["version"])
    except Exception as e:  # noqa: BLE001
        logger.debug(f"[runtime] Nie udało się odczytać wersji z pyproject: {e}")
        return "0.0.0"


def log_backend_modes() -> bool:
    """Loguje tryb współdzielonego stanu. Zwraca True jeśli Redis aktywny."""
    url = os.environ.get("REDIS_URL")
    if redis_reachable(url):
        logger.info(
            f"[runtime] Redis AKTYWNY ({url}) — rate-limit/cache/lock/queue: "
            "tryb ROZPROSZONY (bezpieczny dla wielu workerów)."
        )
        return True
    if url:
        logger.warning(
            f"[runtime] REDIS_URL ustawiony ({url}), ale Redis NIEosiągalny — "
            "degradacja do trybu PROCES-LOKALNY. Sprawdź połączenie z Redisem."
        )
    else:
        logger.warning(
            "[runtime] Brak REDIS_URL — rate-limit/cache/lock w trybie PROCES-LOKALNY. "
            "OK dla 1 procesu. Przy WIELU workerach USTAW REDIS_URL: limity liczą się "
            "per-worker, a distributed lock nie chroni approve między procesami."
        )
    return False
