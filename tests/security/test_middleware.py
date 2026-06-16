"""FIX-02 S3.3: kanoniczna warstwa PII — API stateful per-workspace.

Po konsolidacji security/pii hostuje implementację produkcyjną:
anonymize(text, workspace_id)->str ; deanonymize(text, workspace_id)->str.
"""

import pytest

from smartmyodoo.security.pii.middleware import PiiMiddleware


@pytest.fixture
def pii_middleware():
    return PiiMiddleware()


def test_anonymize_and_deanonymize(pii_middleware):
    original_text = "Firma Jana Kowalskiego o numerze NIP 1234567890 założyła konto."

    anonymized = pii_middleware.anonymize(original_text, workspace_id="ws")

    assert "Jana Kowalskiego" not in anonymized
    assert "1234567890" not in anonymized
    assert "<PERSON" in anonymized
    assert "<NIP" in anonymized

    # Roundtrip — pełne przywrócenie z mappingu workspace'u
    restored = pii_middleware.deanonymize(anonymized, workspace_id="ws")
    assert restored == original_text


def test_deanonymize_multiple_occurrences(pii_middleware):
    original_text = "Mój NIP to 9876543210. Powtarzam: NIP 9876543210."

    anonymized = pii_middleware.anonymize(original_text, workspace_id="ws")
    assert "9876543210" not in anonymized
    # ten sam oryginał → ten sam token (stabilne mapowanie w obrębie workspace'u)
    assert anonymized.count("<NIP_1>") == 2

    restored = pii_middleware.deanonymize(anonymized, workspace_id="ws")
    assert restored == original_text


def test_workspace_isolation(pii_middleware):
    a1 = pii_middleware.anonymize("Faktura dla Jan Kowalski", workspace_id="ws_1")
    a2 = pii_middleware.anonymize("Faktura dla Anna Nowak", workspace_id="ws_2")

    # deanonimizacja respektuje mapping właściwego workspace'u
    assert "Jan Kowalski" in pii_middleware.deanonymize(a1, workspace_id="ws_1")
    assert "Anna Nowak" in pii_middleware.deanonymize(a2, workspace_id="ws_2")
    # token z ws_1 nie deanonimizuje się mappingiem ws_2
    assert "Jan Kowalski" not in pii_middleware.deanonymize(a1, workspace_id="ws_2")
