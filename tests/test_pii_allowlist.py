"""TRUST-01 T2: allow-lista terminów biznesowych w warstwie PII.

Cel (US-T2): presidio NAD-maskuje terminy biznesowe (Price→LOCATION,
Audtyt Hinduskich→PERSON). Allow-lista ma odsiać te false-positive,
ale NIE WOLNO jej osłabić maskowania realnych osób/e-maili (Sekcja D).

Dowody z sesji diagnostycznej 2026-06-25 (presidio na żywych nazwach RMO):
  'Price list possibility' -> '<LOCATION_1> list possibility'  (false-positive)
  'Audtyt Hinduskich modułów' -> '<PERSON_1> modułów'          (false-positive)
  'RMO Henk Molenkamp' -> 'RMO <PERSON_1>'                     (POPRAWNE — nazwisko)
"""

import pytest

from smartmyodoo.security.pii.middleware import PiiMiddleware


@pytest.fixture(scope="module")
def mw():
    # PiiMiddleware ładuje spacy+presidio (drogie) — jeden raz na moduł.
    return PiiMiddleware()


def test_business_term_price_not_masked(mw):
    out = mw.anonymize("Price list possibility", workspace_id="t2_price")
    assert "Price" in out, "termin biznesowy 'Price' nie powinien być maskowany"
    assert "<LOCATION" not in out
    assert "<PERSON" not in out


def test_business_term_audit_not_masked(mw):
    # 'Audtyt' = literówka realnej nazwy zadania w RMO (Audyt). Span 'Audtyt
    # Hinduskich' był maskowany jako PERSON — to nazwa zadania, nie osoba.
    out = mw.anonymize("Audtyt Hinduskich modułów", workspace_id="t2_audit")
    assert "<PERSON" not in out, "nazwa zadania z 'Audyt' nie jest osobą"
    assert "Audtyt" in out


def test_audyt_keyword_not_masked(mw):
    out = mw.anonymize("Audyt bezpieczeństwa systemu", workspace_id="t2_audyt2")
    assert "<PERSON" not in out
    assert "<LOCATION" not in out


def test_real_person_surname_still_masked(mw):
    # KONTROLA BEZPIECZEŃSTWA (Sekcja D): nazwisko MUSI dalej być maskowane.
    out = mw.anonymize("RMO Henk Molenkamp", workspace_id="t2_person")
    assert "Henk" not in out
    assert "Molenkamp" not in out
    assert "<PERSON" in out


def test_email_still_masked(mw):
    # Allow-lista NIE odsłania e-maili (Sekcja D).
    out = mw.anonymize(
        "Kontakt: henk@example.com w sprawie Price list", workspace_id="t2_email"
    )
    assert "henk@example.com" not in out
    # ...ale 'Price' w tym samym zdaniu pozostaje jawne
    assert "Price" in out


def test_mixed_business_and_person(mw):
    # 'Invoice' biznesowe -> jawne; 'Kowalski' osoba -> maskowane.
    out = mw.anonymize("Invoice dla Jan Kowalski", workspace_id="t2_mixed")
    assert "Invoice" in out
    assert "Kowalski" not in out
    assert "<PERSON" in out
