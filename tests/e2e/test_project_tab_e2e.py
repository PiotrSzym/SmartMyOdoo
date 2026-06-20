"""E2E: zakładka Projekt renderuje DOKŁADNIE jeden ze stanów (1/2/3).

Test był wcześniej brittle: twardo zakładał STAN 1 (formularz credentials), bo
„po świeżym zalogowaniu workspace ma project_ref=''". To założenie zależy od stanu
dev-vaultu:
  - gdy workspace jest związany z projektem (project_ref!='') → renderProjectTab() pokazuje STAN 3,
  - gdy istnieje globalny sekret `default_ODOO` → STAN 2 (wybór projektu),
  - dopiero brak project_ref ORAZ brak default_ODOO → STAN 1.
W realnym dev-vaultcie (`default` związany z projektem 42, sekret `default_ODOO` istnieje)
żaden workspace nie pokazuje STANU 1 — stąd fałszywy fail (zdiagnozowane przez /qa UX-10).

Naprawa: zamiast zakładać KTÓRY stan, weryfikujemy INWARIANT renderu (showState, project.js:45):
po wejściu na Skarbiec wyrenderowany jest DOKŁADNIE jeden `#project-state-*` (klasa `flex`),
a pozostałe są ukryte. To pokrywa istotę „wielostanowej zakładki Projekt" niezależnie od danych
i jest spójne ze wzorcem dowodowym z testów UX-10 (marker `flex` = render JS, nie statyczny DOM).
"""

from playwright.sync_api import Page, expect

from .conftest import login_to_dashboard


def test_project_tab_renders_exactly_one_state(page: Page):
    """Skarbiec po loginie renderuje dokładnie jeden ze stanów 1/2/3 (inwariant showState)."""
    login_to_dashboard(page)

    # Wejście na zakładkę Skarbiec/Projekt.
    page.locator("#tab-settings").click()
    expect(page.locator("#settings-screen")).to_be_visible(timeout=5000)

    # MOC DOWODOWA (jak w UX-10): klasa `flex` pojawia się WYŁĄCZNIE przez showState() —
    # statyczny `block`/`hidden` w HTML się nie liczy. Czekamy aż render JS odpali.
    page.wait_for_function(
        "() => [1,2,3].some(n => {"
        "  const el = document.getElementById('project-state-' + n);"
        "  return el && el.classList.contains('flex');"
        "})",
        timeout=12000,
    )

    # Inwariant showState: DOKŁADNIE jeden stan wyrenderowany (flex), pozostałe ukryte.
    rendered = page.evaluate(
        "() => [1,2,3].filter(n => {"
        "  const el = document.getElementById('project-state-' + n);"
        "  return el && el.classList.contains('flex');"
        "})"
    )
    assert len(rendered) == 1, (
        f"Zakładka Projekt powinna pokazać DOKŁADNIE jeden stan (flex), pokazała: {rendered} "
        f"— złamany inwariant showState() (project.js:45)"
    )

    active = rendered[0]
    for n in (1, 2, 3):
        if n == active:
            expect(page.locator(f"#project-state-{n}")).to_be_visible()
        else:
            expect(page.locator(f"#project-state-{n}")).to_be_hidden()
