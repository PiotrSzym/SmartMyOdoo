"""FIX-02 S3.3: KANONICZNA warstwa PII (pseudonimizacja na granicy LLM).

Jedna implementacja (wcześniej zduplikowana: mcp/pii_middleware.py + tu).
API stateful per-workspace — zgodne z produkcją (executor/api/mcp server):
  anonymize(text, workspace_id) -> str ; deanonymize(text, workspace_id) -> str
Mapowania trzymane per workspace_id (izolacja kontekstów).
"""

from typing import Dict

from presidio_anonymizer import AnonymizerEngine

from smartmyodoo.security.pii.recognizers import (
    is_business_term_span,
    setup_analyzer,
)


class PiiMiddleware:
    def __init__(self) -> None:
        self.analyzer = setup_analyzer()
        self.anonymizer = AnonymizerEngine()
        # Mappings: workspace_id -> { entity_token: original_text }
        self.mappings: Dict[str, Dict[str, str]] = {}
        # Counters: workspace_id -> { entity_type: count }
        self.counters: Dict[str, Dict[str, int]] = {}

    def anonymize(self, text: str, workspace_id: str = "default") -> str:
        if not text:
            return text

        results = self.analyzer.analyze(text=text, language="pl")

        # TRUST-01 T2: odsiej false-positive na terminach biznesowych Odoo
        # (Price/Audyt/Invoice…). NIE rusza wzorców osób/e-maili/NIP/PESEL —
        # 'Henk Molenkamp' (brak terminu) przechodzi dalej i jest maskowany.
        results = [r for r in results if not is_business_term_span(text[r.start : r.end])]

        # Filter overlapping entities keeping the highest score
        results = sorted(results, key=lambda x: x.score, reverse=True)
        filtered_results: list = []
        for res in results:
            overlap = False
            for f_res in filtered_results:
                if res.start < f_res.end and res.end > f_res.start:
                    overlap = True
                    break
            if not overlap:
                filtered_results.append(res)

        # Sort reverse by start index for safe replacement
        filtered_results = sorted(filtered_results, key=lambda x: x.start, reverse=True)

        if workspace_id not in self.mappings:
            self.mappings[workspace_id] = {}
        if workspace_id not in self.counters:
            self.counters[workspace_id] = {}

        anonymized_text = text
        for res in filtered_results:
            original = text[res.start : res.end]
            entity_type = res.entity_type

            # Check if this exact string was already mapped in this workspace
            existing_token = None
            for token, orig_val in self.mappings[workspace_id].items():
                if orig_val == original and token.startswith(f"<{entity_type}_"):
                    existing_token = token
                    break

            if existing_token:
                token = existing_token
            else:
                count = self.counters[workspace_id].get(entity_type, 0) + 1
                self.counters[workspace_id][entity_type] = count
                token = f"<{entity_type}_{count}>"
                self.mappings[workspace_id][token] = original

            anonymized_text = (
                anonymized_text[: res.start] + token + anonymized_text[res.end :]
            )

        return anonymized_text

    def deanonymize(self, text: str, workspace_id: str = "default") -> str:
        if not text or workspace_id not in self.mappings:
            return text

        mapping = self.mappings[workspace_id]
        deanonymized_text = text
        for token, original in mapping.items():
            deanonymized_text = deanonymized_text.replace(token, original)

        return deanonymized_text
