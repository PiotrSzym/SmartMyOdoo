"""DOC-01: test RENDERU Centrum Dokumentacji (browser, Playwright).

Łapie regresję, której nie wykryje test plikowy: po loginie + kliknięciu zakładki
ekran NIE może być pusty (sidebar + treść sekcji muszą się wyrenderować).

Wymaga działającego serwera na :8000 (start: `python -m uvicorn smartmyodoo.api:app`)
oraz zainicjalizowanego vaulta z PIN 1111. Bez serwera test jest pomijany (skip).
"""

import socket

import pytest


def _server_up(port: int = 8000) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0


pytestmark = pytest.mark.skipif(
    not _server_up(), reason="serwer :8000 nieaktywny — test renderu UI pominięty"
)


@pytest.mark.asyncio
async def test_docs_tab_renders_content():
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        pytest.skip("playwright niezainstalowany")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        page_errors: list = []
        page.on("pageerror", lambda e: page_errors.append(str(e)))
        try:
            await page.goto("http://127.0.0.1:8000/", wait_until="networkidle")
            # login PIN 1111 (jeśli ekran logowania)
            if await page.locator("#auth-password").count():
                await page.fill("#auth-password", "1111")
                await page.click("text=Odblokuj")
                await page.wait_for_timeout(1500)
            await page.click("#tab-docs")
            await page.wait_for_timeout(600)
            info = await page.evaluate(
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
        finally:
            await browser.close()

    assert not page_errors, f"błędy JS na stronie: {page_errors[:3]}"
    assert info["hidden"] is False, "ekran dokumentacji pozostał ukryty po kliknięciu"
    assert info["sidebar"] == 8, f"oczekiwano 8 sekcji w menu, jest {info['sidebar']}"
    assert info["hasSearch"], "brak pola wyszukiwarki"
    assert (
        info["textLen"] > 100
    ), f"ekran dokumentacji praktycznie PUSTY (textLen={info['textLen']}) — regresja renderu"
