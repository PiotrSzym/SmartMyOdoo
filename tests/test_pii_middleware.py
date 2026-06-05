from smartmyodoo.mcp.pii_middleware import PiiMiddleware


def test_roundtrip_anonymization():
    middleware = PiiMiddleware()
    text = "Faktura dla Jan Kowalski, NIP 1234563218"

    anonymized_text = middleware.anonymize(text, workspace_id="ws_1")

    # Weryfikacja
    assert "Jan" not in anonymized_text
    assert "Kowalski" not in anonymized_text
    assert "1234563218" not in anonymized_text
    assert "<persName" in anonymized_text
    assert "<NIP" in anonymized_text

    # Deanonimizacja
    deanonymized_text = middleware.deanonymize(anonymized_text, workspace_id="ws_1")

    assert "Jan Kowalski" in deanonymized_text
    assert "1234563218" in deanonymized_text
    assert text == deanonymized_text


def test_workspace_isolation():
    middleware = PiiMiddleware()
    text1 = "Faktura dla Jan Kowalski"
    text2 = "Faktura dla Anna Nowak"

    anon1 = middleware.anonymize(text1, workspace_id="ws_1")
    anon2 = middleware.anonymize(text2, workspace_id="ws_2")

    assert "<persName" in anon1
    assert "<persName" in anon2

    de1 = middleware.deanonymize(anon1, workspace_id="ws_1")
    de2 = middleware.deanonymize(anon2, workspace_id="ws_2")

    assert "Jan Kowalski" in de1
    assert "Anna Nowak" in de2
