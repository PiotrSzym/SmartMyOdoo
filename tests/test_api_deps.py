"""FIX-02 S3.4: dowód zerwania cyklu importów (deps-module).

Regresja: gdy `api.py` startował jako `__main__` (`python -m smartmyodoo.api`),
routery robiły `from smartmyodoo.api import require_auth` → ImportError
(partially initialized module). Po wydzieleniu `api_deps` routery zależą tylko
od `api_deps`, więc import routera NIE wciąga `api.py`.
"""

import subprocess
import sys


def test_router_import_does_not_pull_in_api():
    """Import routera w świeżym interpreterze nie ładuje smartmyodoo.api.

    RED przed S3.4 (router importował require_auth z api → api w sys.modules).
    GREEN po S3.4 (router importuje z api_deps).
    """
    code = (
        "import smartmyodoo.api_routers.proposals as p;"
        "import smartmyodoo.api_routers.models as m;"
        "import smartmyodoo.api_routers.workspaces as w;"
        "import smartmyodoo.api_routers.monitoring as mo;"
        "assert all(hasattr(x, 'router') for x in (p, m, w, mo));"
        "import sys;"
        "assert 'smartmyodoo.api' not in sys.modules, 'router nie powinien ladowac api.py';"
        "print('OK')"
    )
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert r.returncode == 0, f"stderr={r.stderr}"
    assert "OK" in r.stdout


def test_api_reexports_are_identical_to_deps():
    """`from smartmyodoo.api import require_auth` to ten sam obiekt co w api_deps."""
    from smartmyodoo import api, api_deps

    assert api.require_auth is api_deps.require_auth
    assert api.get_auth_key is api_deps.get_auth_key


def test_routers_import_auth_from_api_deps():
    """Statyczna gwarancja: żaden router nie importuje auth z smartmyodoo.api."""
    import pathlib

    root = pathlib.Path(__file__).resolve().parents[1] / "smartmyodoo" / "api_routers"
    offenders = []
    for f in root.glob("*.py"):
        text = f.read_text(encoding="utf-8")
        if "from smartmyodoo.api import require_auth" in text:
            offenders.append(f.name)
    assert not offenders, f"routery importują auth z api zamiast api_deps: {offenders}"
