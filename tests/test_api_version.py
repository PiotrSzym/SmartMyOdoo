"""RELEASE-01 / T5 (US-REL-5): endpoint /api/version zwraca wersję wydania.

`/api/version` czyta wersję z metadanych zainstalowanego pakietu
(`importlib.metadata.version('smartmyodoo')`), z fallbackiem na odczyt `pyproject.toml`.
SSoT wersji = `pyproject.toml` (D4). Endpoint jest publiczny (jak /api/status) i nie
eksponuje danych wrażliwych (Sekcja D) — tylko numer wersji.
"""

import re

from fastapi.testclient import TestClient

from smartmyodoo.api import app

client = TestClient(app)

# Luźny semver: X.Y.Z (+ ewentualne pre/local), wystarczy do walidacji formatu.
_SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+")


def test_version_endpoint_returns_string_version():
    resp = client.get("/api/version")
    assert resp.status_code == 200
    body = resp.json()
    assert "version" in body, f"brak pola 'version' w odpowiedzi: {body}"
    version = body["version"]
    assert isinstance(version, str) and version, "wersja musi być niepustym stringiem"
    assert _SEMVER_RE.match(version), f"wersja '{version}' nie wygląda na semver X.Y.Z"


def test_version_matches_pyproject_ssot():
    """SSoT (D4): wersja z /api/version musi odpowiadać `version` z pyproject.toml."""
    import os
    import tomllib

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(root, "pyproject.toml"), "rb") as fh:
        pyproject_version = tomllib.load(fh)["project"]["version"]

    resp = client.get("/api/version")
    assert resp.status_code == 200
    assert resp.json()["version"] == pyproject_version, (
        "wersja /api/version rozjechała się z pyproject.toml (SSoT)"
    )


def test_version_endpoint_is_public_no_auth_required():
    """Parytet z /api/status: wersja jest publiczna (brak 401 bez tokenu)."""
    resp = client.get("/api/version")
    assert resp.status_code != 401
