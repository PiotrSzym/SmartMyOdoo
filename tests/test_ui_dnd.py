import asyncio
from playwright.async_api import async_playwright
import socket


def is_port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("localhost", port)) == 0


async def run_test():
    if not is_port_in_use(8000):
        print(
            "Błąd: Serwer na porcie 8000 nie odpowiada. Włącz `python smartmyodoo/api.py` by wykonać ten test."
        )
        return

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # Catch errors
        errors = []
        page.on(
            "console",
            lambda msg: errors.append(f"Browser Console: {msg.type}: {msg.text}")
            if msg.type == "error"
            else None,
        )
        page.on("pageerror", lambda err: errors.append(f"Browser Error: {err}"))

        await page.goto("http://localhost:8000")

        # In case we need to init
        if await page.locator("#init-master").is_visible():
            await page.fill("#init-master", "testmaster")
            await page.fill("#init-pin", "1234")
            await page.click("button:has-text('Inicjuj Skarbiec')")
            await page.wait_for_timeout(1000)

        # Login
        if await page.locator("#login-pin").is_visible():
            await page.fill("#login-pin", "1234")
            await page.click("button:has-text('Odblokuj')")
            await page.wait_for_timeout(1000)

        print("Testing Delete Modal...")
        # Add workspace
        await page.click("text='Nowy Wpis'")
        await page.fill("input[placeholder='Nazwa, np. Dev Server']", "TestWS_E2E")
        await page.fill("input[placeholder='https://odoo.local']", "http://test.loc")
        await page.click("button:has-text('Zapisz')")
        await page.wait_for_timeout(1000)

        ws_items = await page.locator(".ws-item").all()
        if len(ws_items) > 0:
            await ws_items[0].hover()
            del_btn = ws_items[0].locator(".ws-delete-btn")
            await del_btn.click()
            await page.wait_for_timeout(500)

            # Check if modal is visible
            is_visible = await page.locator("#delete-ws-modal").is_visible()
            print(f"Delete modal visible: {is_visible}")

            # Close the modal
            await page.click("button:has-text('Anuluj')")
            await page.wait_for_timeout(500)

        print("Testing Drag and Drop...")
        # Create second workspace to test D&D
        await page.click("text='Nowy Wpis'")
        await page.fill("input[placeholder='Nazwa, np. Dev Server']", "TestWS_E2E_2")
        await page.fill("input[placeholder='https://odoo.local']", "http://test2.loc")
        await page.click("button:has-text('Zapisz')")
        await page.wait_for_timeout(1000)

        await page.evaluate("""
            const items = document.querySelectorAll('.ws-item');
            if(items.length > 1) {
                const source = items[0];
                const target = items[1];
                const dt = new DataTransfer();
                source.dispatchEvent(new DragEvent('dragstart', { dataTransfer: dt }));
                target.dispatchEvent(new DragEvent('dragenter', { dataTransfer: dt }));
                target.dispatchEvent(new DragEvent('dragover', { dataTransfer: dt, clientY: target.getBoundingClientRect().bottom - 1 }));
                target.dispatchEvent(new DragEvent('drop', { dataTransfer: dt, clientY: target.getBoundingClientRect().bottom - 1 }));
                source.dispatchEvent(new DragEvent('dragend'));
            }
        """)
        await page.wait_for_timeout(1000)
        print("D&D Completed.")

        if errors:
            print("Zanotowano błędy JS na konsoli przeglądarki:")
            for e in errors:
                print(e)
            exit(1)
        else:
            print("0 błędów! Test UI zakończony sukcesem.")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(run_test())
