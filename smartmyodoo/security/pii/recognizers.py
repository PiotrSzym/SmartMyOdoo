"""FIX-02 S3.3: KANONICZNE recognizery PL PII + budowa analyzera.

Jedna implementacja (wcześniej zduplikowana w mcp/pii_recognizers.py + tu).
Zachowuje zachowanie produkcyjne (entity NIP/PESEL, regex bez myślników, score 0.6,
mapowanie persName→PERSON / orgName→ORGANIZATION / placeName→LOCATION).

FOLLOW-UP (poza S3.3, bo zmiana zachowania detekcji): wariant NIP z myślnikami
(`123-456-78-90`, score 0.8) z dawnego stateless PII — do rozważenia jako wzmocnienie.
"""

from presidio_analyzer import (
    AnalyzerEngine,
    RecognizerRegistry,
    PatternRecognizer,
    Pattern,
)
from presidio_analyzer.nlp_engine import NlpEngineProvider


class NipRecognizer(PatternRecognizer):
    def __init__(self):
        patterns = [Pattern("NIP Pattern", r"\b\d{10}\b", 0.6)]
        super().__init__(
            supported_entity="NIP", patterns=patterns, supported_language="pl"
        )


class PeselRecognizer(PatternRecognizer):
    def __init__(self):
        patterns = [Pattern("PESEL Pattern", r"\b\d{11}\b", 0.6)]
        super().__init__(
            supported_entity="PESEL", patterns=patterns, supported_language="pl"
        )


def setup_analyzer() -> AnalyzerEngine:
    configuration = {
        "nlp_engine_name": "spacy",
        "models": [{"lang_code": "pl", "model_name": "pl_core_news_md"}],
        "ner_model_configuration": {
            "labels_to_ignore": [],
            "model_to_presidio_entity_mapping": {
                "persName": "PERSON",
                "orgName": "ORGANIZATION",
                "placeName": "LOCATION",
            },
        },
    }
    provider = NlpEngineProvider(nlp_configuration=configuration)
    nlp_engine = provider.create_engine()

    registry = RecognizerRegistry()
    registry.supported_languages = ["pl"]
    registry.load_predefined_recognizers(nlp_engine=nlp_engine, languages=["pl"])

    registry.add_recognizer(NipRecognizer())
    registry.add_recognizer(PeselRecognizer())

    analyzer = AnalyzerEngine(
        registry=registry, nlp_engine=nlp_engine, supported_languages=["pl"]
    )
    return analyzer
