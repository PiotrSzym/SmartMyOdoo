"""FIX-02 S3.3: KANONICZNE recognizery PL PII + budowa analyzera.

Jedna implementacja (wcześniej zduplikowana w mcp/pii_recognizers.py + tu).
Zachowuje zachowanie produkcyjne (entity NIP/PESEL, regex bez myślników, score 0.6,
mapowanie persName→PERSON / orgName→ORGANIZATION / placeName→LOCATION).

FOLLOW-UP (poza S3.3, bo zmiana zachowania detekcji): wariant NIP z myślnikami
(`123-456-78-90`, score 0.8) z dawnego stateless PII — do rozważenia jako wzmocnienie.
"""

import re

from presidio_analyzer import (
    AnalyzerEngine,
    RecognizerRegistry,
    PatternRecognizer,
    Pattern,
)
from presidio_analyzer.nlp_engine import NlpEngineProvider

# TRUST-01 T2 (2026-06-25): allow-lista terminów BIZNESOWYCH.
# Presidio NAD-maskuje słownictwo Odoo jako PII: 'Price'→LOCATION,
# 'Audtyt Hinduskich'→PERSON (false-positive na nazwach projektów/zadań).
# Reguła: detekcję PII USUWAMY, gdy jej span zawiera któryś z tych terminów
# jako SAMODZIELNE SŁOWO. Terminy to wyłącznie rzeczowniki domeny Odoo —
# NIGDY wzorce osób/e-maili/telefonów (Sekcja D / ADR-011). Dzięki temu
# 'Henk Molenkamp' (brak terminu) dalej jest maskowany.
# 'Audtyt' celowo obok 'Audyt' — to realna literówka w nazwie zadania RMO.
BUSINESS_ALLOWLIST = frozenset(
    {
        "price",
        "audit",
        "audyt",
        "audtyt",
        "invoice",
        "faktura",
        "faktury",
        "sale",
        "sales",
        "sprzedaż",
        "order",
        "zamówienie",
        "stock",
        "magazyn",
        "list",
        "lista",
        "project",
        "projekt",
        "task",
        "zadanie",
        "zadania",
        "possibility",
        "możliwość",
        "type",
        "report",
        "raport",
        "module",
        "moduł",
        "moduły",
        "modułów",
    }
)

# Granice słowa unicode-aware (polskie znaki). Span dzielimy na słowa i
# sprawdzamy przecięcie z allow-listą (case-insensitive).
_WORD_RE = re.compile(r"\w+", re.UNICODE)


def is_business_term_span(matched_text: str) -> bool:
    """Czy span detekcji PII zawiera termin biznesowy jako samodzielne słowo.

    True => detekcja to false-positive na słownictwie Odoo, NIE maskujemy.
    Sprawdzamy WYŁĄCZNIE terminy z BUSINESS_ALLOWLIST (rzeczowniki domeny) —
    żaden wzorzec osoby/e-maila nie jest tu osłabiany.
    """
    if not matched_text:
        return False
    words = {w.lower() for w in _WORD_RE.findall(matched_text)}
    return bool(words & BUSINESS_ALLOWLIST)


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
