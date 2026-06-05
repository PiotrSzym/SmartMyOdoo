from typing import Dict
from presidio_analyzer import AnalyzerEngine, RecognizerRegistry
from presidio_analyzer.nlp_engine import NlpEngineProvider, NerModelConfiguration
from smartmyodoo.security.pii.recognizers import NipRecognizer, PeselRecognizer


class AnonymizedResult:
    def __init__(self, text: str, mapping: Dict[str, str]):
        self.text = text
        self.mapping = mapping


class PiiMiddleware:
    def __init__(self):
        registry = RecognizerRegistry(supported_languages=["pl"])
        registry.load_predefined_recognizers(languages=["pl"])
        registry.add_recognizer(NipRecognizer())
        registry.add_recognizer(PeselRecognizer())

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

        self.analyzer = AnalyzerEngine(
            registry=registry, nlp_engine=nlp_engine, supported_languages=["pl"]
        )

    def anonymize(self, text: str) -> AnonymizedResult:
        results = self.analyzer.analyze(text=text, language="pl")
        results = sorted(results, key=lambda x: x.start)

        mapping: Dict[str, str] = {}
        type_counters: Dict[str, int] = {}

        anonymized_text = ""
        last_end = 0

        for res in results:
            if res.start < last_end:
                continue

            entity_type = res.entity_type
            if entity_type not in type_counters:
                type_counters[entity_type] = 1

            original_value = text[res.start : res.end]

            token_for_value = None
            for token, val in mapping.items():
                if val == original_value:
                    token_for_value = token
                    break

            if not token_for_value:
                token_for_value = f"<{entity_type}_{type_counters[entity_type]}>"
                type_counters[entity_type] += 1
                mapping[token_for_value] = original_value

            anonymized_text += text[last_end : res.start] + token_for_value
            last_end = res.end

        anonymized_text += text[last_end:]

        return AnonymizedResult(anonymized_text, mapping)

    def deanonymize(self, text: str, mapping: Dict[str, str]) -> str:
        restored_text = text
        for token, value in mapping.items():
            restored_text = restored_text.replace(token, value)
        return restored_text
