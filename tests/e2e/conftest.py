"""Oznacza testy w tests/e2e/ markerem `e2e`.

Testy e2e (Playwright) wymagają żywego serwera + chromium i używają sync API Playwright,
które trzyma własną pętlę zdarzeń. Bez izolacji psuły kolejne testy async w pełnym przebiegu
(`RuntimeError: Runner.run() cannot be called from a running event loop`).
Domyślnie wykluczone przez `addopts = "-m 'not e2e'"`. Uruchom jawnie: `pytest -m e2e`.
"""

import pathlib

import pytest

_E2E_DIR = pathlib.Path(__file__).parent.resolve()


def pytest_collection_modifyitems(config, items):
    # Hook jest wołany sesyjnie (items = WSZYSTKIE testy) — oznacz tylko te z tego katalogu.
    for item in items:
        try:
            item_path = pathlib.Path(str(item.fspath)).resolve()
        except Exception:
            continue
        if _E2E_DIR == item_path.parent or _E2E_DIR in item_path.parents:
            item.add_marker(pytest.mark.e2e)
