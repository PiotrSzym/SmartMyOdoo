from typing import Dict, Any
import json
import logging

logger = logging.getLogger(__name__)

# 8-Krokowy Agent Decision Protocol (Chain-of-Thought)
ADP_SYSTEM_PROMPT = """Jesteś wyspecjalizowanym Agentem Odoo (Persona: {persona}).
Twoim zadaniem jest przeprowadzenie rygorystycznego 8-krokowego protokołu decyzyjnego (ADP) przed wykonaniem jakiejkolwiek akcji.

KROKI ADP:
1. Historia: Co robiłeś poprzednio? (Jeśli nic, wpisz 'Brak')
2. Kontekst: Gdzie obecnie się znajdujesz i jaki jest Twój stan wiedzy?
3. Wersja Odoo: Dla jakiej wersji Odoo przygotowujesz rozwiązanie?
4. Practices: Jakie Golden Rules z dokumentacji musisz zastosować?
5. Analiza: Rozłóż intencję użytkownika na czynniki pierwsze.
6. Trudność: Oceń trudność od 1 do 10.
7. Research: Czy potrzebujesz więcej danych z Bazy Wiedzy (Shared Brain)?
8. Plan: Skonstruuj dokładny plan akcji (ACTUATION).

Intencja użytkownika:
"{intent}"

Zwróć wynik jako JSON z kluczami odpowiadającymi krokom (1-8). Zawsze zwracaj tylko poprawny obiekt JSON.
"""


class DecisionEngine:
    """
    Silnik uruchamiający Agent Decision Protocol.
    Wymaga instancji llm_client.
    """

    def __init__(self, llm_client=None):
        self.llm_client = llm_client

    def evaluate(self, persona: str, intent: str) -> Dict[str, Any]:
        """
        Ocenia intencję użytkownika używając 8-krokowego ADP.
        Zwraca wygenerowany przez LLM plan w formacie dict.
        """
        if not self.llm_client:
            logger.warning("Brak llm_client. Używam mockowego ADP.")
            return self._mock_adp(persona, intent)

        prompt = ADP_SYSTEM_PROMPT.format(persona=persona, intent=intent)

        try:
            response = self.llm_client.chat(prompt)
            data = json.loads(response)
            return data
        except Exception as e:
            logger.error(f"Błąd podczas ewaluacji ADP: {str(e)}")
            return self._mock_adp(persona, intent)

    def _mock_adp(self, persona: str, intent: str) -> Dict[str, Any]:
        """Zwraca atrapę decyzji do celów testowych/fallbackowych."""
        return {
            "1_Historia": "Brak",
            "2_Kontekst": f"Otrzymano zadanie dla {persona}",
            "3_Wersja": "Odoo 18",
            "4_Practices": "TDD, brak bezpośrednich modyfikacji bazy",
            "5_Analiza": intent,
            "6_Trudnosc": 3,
            "7_Research": "Nie",
            "8_Plan": "Wykonaj akcję standardową na bazie Scratchpad DB.",
        }
