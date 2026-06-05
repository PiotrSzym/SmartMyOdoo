import pytest
from presidio_analyzer import AnalyzerEngine, RecognizerRegistry
from smartmyodoo.security.pii.recognizers import NipRecognizer, PeselRecognizer


@pytest.fixture
def analyzer():
    registry = RecognizerRegistry(supported_languages=["pl"])
    registry.load_predefined_recognizers(languages=["pl"])

    # Add custom recognizers
    registry.add_recognizer(NipRecognizer())
    registry.add_recognizer(PeselRecognizer())

    # NLP Engine using Polish Spacy
    # Note: spacy model pl_core_news_md must be installed
    from presidio_analyzer.nlp_engine import NlpEngineProvider, NerModelConfiguration

    # In Polish spacy models, PERSON is often labeled as persName
    ner_configuration = NerModelConfiguration(
        labels_to_ignore=[], model_to_presidio_entity_mapping={"persName": "PERSON"}
    )

    configuration = {
        "nlp_engine_name": "spacy",
        "models": [{"lang_code": "pl", "model_name": "pl_core_news_md"}],
        "ner_model_configuration": ner_configuration.to_dict(),
    }
    provider = NlpEngineProvider(nlp_configuration=configuration)
    nlp_engine = provider.create_engine()

    return AnalyzerEngine(
        registry=registry, nlp_engine=nlp_engine, supported_languages=["pl"]
    )


def test_nip_recognition(analyzer):
    text = "Firma posiada NIP 1234567890 oraz inny NIP: 123-456-78-90."
    results = analyzer.analyze(text=text, language="pl", entities=["PL_NIP"])
    assert len(results) == 2, f"Oczekiwano 2 wyników PL_NIP, znaleziono {len(results)}"

    entities_texts = [text[res.start : res.end] for res in results]
    assert "1234567890" in entities_texts
    assert "123-456-78-90" in entities_texts


def test_pesel_recognition(analyzer):
    text = "Jan Kowalski, pesel 90010112345. Posiada pesel: 90010112345"
    results = analyzer.analyze(text=text, language="pl", entities=["PL_PESEL"])
    assert (
        len(results) == 2
    ), f"Oczekiwano 2 wyników PL_PESEL, znaleziono {len(results)}"

    entities_texts = [text[res.start : res.end] for res in results]
    assert "90010112345" in entities_texts


def test_person_name_recognition(analyzer):
    text = (
        "Spotkanie z Janem Kowalskim odbyło się w biurze. Anna Nowak również tam była."
    )
    # Używamy standardowego PERSON
    results = analyzer.analyze(text=text, language="pl", entities=["PERSON"])

    # Spacy w wersji polskiej powinno znaleźć Jana Kowalskiego i Annę Nowak
    # Odmiany mogą zostać rozpoznane ("Janem Kowalskim")
    assert (
        len(results) >= 2
    ), f"Oczekiwano minimum 2 wyników PERSON, znaleziono {len(results)}"
