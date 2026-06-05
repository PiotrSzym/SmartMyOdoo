import re
from presidio_analyzer import AnalyzerEngine, RecognizerRegistry, PatternRecognizer, Pattern
from presidio_analyzer.nlp_engine import NlpEngineProvider

class NipRecognizer(PatternRecognizer):
    def __init__(self):
        patterns = [Pattern("NIP Pattern", r"\b\d{10}\b", 0.6)]
        super().__init__(supported_entity="NIP", patterns=patterns, supported_language="pl")

class PeselRecognizer(PatternRecognizer):
    def __init__(self):
        patterns = [Pattern("PESEL Pattern", r"\b\d{11}\b", 0.6)]
        super().__init__(supported_entity="PESEL", patterns=patterns, supported_language="pl")

def setup_analyzer() -> AnalyzerEngine:
    configuration = {
        "nlp_engine_name": "spacy",
        "models": [{"lang_code": "pl", "model_name": "pl_core_news_md"}],
    }
    provider = NlpEngineProvider(nlp_configuration=configuration)
    nlp_engine = provider.create_engine()

    registry = RecognizerRegistry()
    registry.supported_languages = ["pl"]
    registry.load_predefined_recognizers(nlp_engine=nlp_engine, languages=["pl"])
    
    registry.add_recognizer(NipRecognizer())
    registry.add_recognizer(PeselRecognizer())
    
    analyzer = AnalyzerEngine(
        registry=registry, 
        nlp_engine=nlp_engine, 
        supported_languages=["pl"]
    )
    return analyzer
