from smartmyodoo.mcp.pii_recognizers import setup_analyzer


def test_nip_recognition():
    analyzer = setup_analyzer()
    text = "Faktura dla firmy o NIP 1234563218 wystawiona."
    results = analyzer.analyze(text=text, entities=["NIP"], language="pl")
    assert len(results) == 1
    assert results[0].entity_type == "NIP"
    assert text[results[0].start : results[0].end] == "1234563218"


def test_pesel_recognition():
    analyzer = setup_analyzer()
    text = "Dane klienta: PESEL 90051412345 to Jan."
    results = analyzer.analyze(text=text, entities=["PESEL"], language="pl")
    assert len(results) == 1
    assert results[0].entity_type == "PESEL"
    assert text[results[0].start : results[0].end] == "90051412345"


def test_polish_person_name_recognition():
    analyzer = setup_analyzer()
    text = "Pan Janusz Kowalski złożył zamówienie."
    results = analyzer.analyze(text=text, language="pl")
    assert len(results) >= 1
    assert any(r.entity_type == "PERSON" for r in results)
