"""FIX-02 S3.3: recognizery PL PII — kanoniczne entity NIP/PESEL/PERSON.

Po konsolidacji security/pii hostuje implementację produkcyjną (entity NIP/PESEL,
regex 10/11 cyfr). Dawny stateless wariant (PL_NIP z myślnikami) wycofany —
detekcja NIP z myślnikami jest udokumentowanym follow-upem (zmiana zachowania).
"""

import pytest

from smartmyodoo.security.pii.recognizers import (
    NipRecognizer,
    PeselRecognizer,
    setup_analyzer,
)


@pytest.fixture
def analyzer():
    return setup_analyzer()


def test_recognizer_entities():
    """Recognizery deklarują kanoniczne entity (NIP/PESEL), nie PL_*."""
    assert NipRecognizer().supported_entities == ["NIP"]
    assert PeselRecognizer().supported_entities == ["PESEL"]


def test_nip_recognition(analyzer):
    text = "Firma posiada NIP 1234567890 w rejestrze."
    results = analyzer.analyze(text=text, language="pl", entities=["NIP"])
    assert len(results) == 1
    assert text[results[0].start : results[0].end] == "1234567890"


def test_pesel_recognition(analyzer):
    text = "Jan Kowalski, pesel 90010112345. Powtarzam pesel: 90010112345"
    results = analyzer.analyze(text=text, language="pl", entities=["PESEL"])
    assert len(results) == 2
    assert all(text[r.start : r.end] == "90010112345" for r in results)


def test_person_name_recognition(analyzer):
    text = "Spotkanie z Janem Kowalskim. Anna Nowak również tam była."
    results = analyzer.analyze(text=text, language="pl", entities=["PERSON"])
    assert len(results) >= 2, f"oczekiwano ≥2 PERSON, znaleziono {len(results)}"
