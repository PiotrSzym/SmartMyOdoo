from presidio_analyzer import PatternRecognizer, Pattern


class NipRecognizer(PatternRecognizer):
    def __init__(self):
        patterns = [
            Pattern(
                name="nip_pattern",
                regex=r"\b[0-9]{3}-?[0-9]{3}-?[0-9]{2}-?[0-9]{2}\b",
                score=0.8,
            )
        ]
        super().__init__(
            supported_entity="PL_NIP",
            patterns=patterns,
            context=["nip", "NIP", "nip:"],
            supported_language="pl",
        )


class PeselRecognizer(PatternRecognizer):
    def __init__(self):
        patterns = [Pattern(name="pesel_pattern", regex=r"\b[0-9]{11}\b", score=0.8)]
        super().__init__(
            supported_entity="PL_PESEL",
            patterns=patterns,
            context=["pesel", "PESEL", "pesel:"],
            supported_language="pl",
        )
