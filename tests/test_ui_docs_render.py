"""DOC-01: test RENDERU Centrum Dokumentacji (browser, Playwright).

Łapie regresję, której nie wykryje test plikowy: po loginie + kliknięciu zakładki
ekran NIE może być pusty (sidebar + treść sekcji muszą się wyrenderować).

Wymaga działającego serwera na :8000 (start: `python -m uvicorn smartmyodoo.api:app`)
oraz zainicjalizowanego vaulta. Bez serwera test jest pomijany (skip).

FIX (ADR-016 follow-up, 2026-07-11): używa fixture `page` z pytest-playwright —
jak CAŁA reszta suity e2e (tests/e2e/*). Wcześniejsze wersje kolidowały pętlami
zdarzeń w pełnym przebiegu `pytest -m e2e`:
- async_api + pytest-asyncio → psuł teardown kolejnych testów (Py3.14: `Runner.run()
  cannot be called from a running event loop`);
- ręczny `sync_playwright()` → sesyjny playwright pluginu trzyma własną, DZIAŁAJĄCĄ
  pętlę asyncio przez całą sesję, więc drugi sync-driver w tym samym wątku odmawia
  (`Playwright Sync API inside the asyncio loop`).
Wspólna fixture `page` = jeden driver/loop na sesję → test niezależny od kolejności.
"""

import os
import socket

import pytest

try:
    import pytest_playwright  # noqa: F401 — tylko detekcja pluginu (fixture `page`)

    _HAS_PLAYWRIGHT = True
except ImportError:
    _HAS_PLAYWRIGHT = False


def _server_up(port: int = 8000) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0


# Test przeglądarkowy (Playwright + żywy serwer) — należy do suity e2e, więc domyślnie
# wykluczony przez `addopts = -m 'not e2e'` (uruchamiaj jawnie: `pytest -m e2e`). Bez tego
# konkurował o zasoby w pełnej suicie i migotał. Skip dodatkowo, gdy serwer :8000 nieaktywny.
pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(
        not _server_up(), reason="serwer :8000 nieaktywny — test renderu UI pominięty"
    ),
    pytest.mark.skipif(
        not _HAS_PLAYWRIGHT, reason="pytest-playwright niezainstalowany"
    ),
]

# PIN 1111 = rola USER — celowo, bo login adminem (np. master/1234) odpala modal
# zmiany PIN-u, który zasłania #tab-docs (conftest e2e musi go zamykać). Nadpisywalny:
# SMARTMYODOO_E2E_PIN.
_PIN = os.environ.get("SMARTMYODOO_E2E_PIN", "1111")


def test_docs_tab_renders_content(page):
    page_errors: list = []
    page.on("pageerror", lambda e: page_errors.append(str(e)))

    # `load` zamiast `networkidle`: ten ostatni czeka na ciszę sieci, której
    # zewnętrzne CDN (Tailwind/Fonts/lucide) potrafią nie osiągnąć w 30s → flaky timeout.
    # Po `load` czekamy jawnie aż UI zdecyduje o ekranie (login albo dashboard).
    page.goto("http://127.0.0.1:8000/", wait_until="load")
    page.wait_for_selector("#auth-password, #tab-docs", timeout=15000)
    # login PIN (jeśli ekran logowania)
    if page.locator("#auth-password").count():
        page.fill("#auth-password", _PIN)
        page.click("text=Odblokuj")
        page.wait_for_timeout(1500)
    page.click("#tab-docs")
    page.wait_for_timeout(600)
    info = page.evaluate(
        """() => {
            const s = document.getElementById('docs-screen');
            return {
                hidden: s.classList.contains('hidden'),
                sidebar: s.querySelectorAll('[data-doc-section]').length,
                hasSearch: !!document.getElementById('docs-search'),
                textLen: (s.innerText || '').trim().length,
            };
        }"""
    )

    assert not page_errors, f"błędy JS na stronie: {page_errors[:3]}"
    assert info["hidden"] is False, "ekran dokumentacji pozostał ukryty po kliknięciu"
    assert info["sidebar"] == 9, f"oczekiwano 9 sekcji w menu, jest {info['sidebar']}"
    assert info["hasSearch"], "brak pola wyszukiwarki"
    assert (
        info["textLen"] > 100
    ), f"ekran dokumentacji praktycznie PUSTY (textLen={info['textLen']}) — regresja renderu"
