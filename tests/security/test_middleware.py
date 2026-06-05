import pytest
from smartmyodoo.security.pii.middleware import PiiMiddleware


@pytest.fixture
def pii_middleware():
    return PiiMiddleware()


def test_anonymize_and_deanonymize(pii_middleware):
    original_text = "Firma Jana Kowalskiego o numerze NIP 123-456-78-90 założyła konto."

    # 1. Anonimizacja
    anonymized_result = pii_middleware.anonymize(original_text)

    assert "Jana Kowalskiego" not in anonymized_result.text
    assert "123-456-78-90" not in anonymized_result.text
    assert "<PERSON" in anonymized_result.text
    assert "<PL_NIP" in anonymized_result.text

    # 2. Deanonimizacja (Roundtrip)
    restored_text = pii_middleware.deanonymize(
        anonymized_result.text, anonymized_result.mapping
    )

    assert restored_text == original_text


def test_deanonymize_multiple_occurrences(pii_middleware):
    original_text = "Mój NIP to 9876543210. Powtarzam: NIP 9876543210."

    # Anonimizacja
    result = pii_middleware.anonymize(original_text)

    assert "9876543210" not in result.text
    assert result.text.count("<PL_NIP") == 2

    # Przywrócenie
    restored_text = pii_middleware.deanonymize(result.text, result.mapping)
    assert restored_text == original_text
