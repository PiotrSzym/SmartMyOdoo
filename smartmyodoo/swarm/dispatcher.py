from typing import Any, Dict

import json

from .models import DispatchResult, IntentCategory, Persona, SkillName

# Wzorzec routingu (Task 1.2 & 1.3)
ROUTING_TABLE: Dict[IntentCategory, Dict[str, Any]] = {
    IntentCategory.A_CODE_GENERATION: {
        "persona": Persona.DEV,
        "skill_name": SkillName.ODOO_DEVELOPER,
        "model": "anthropic/claude-3.5-sonnet",
    },
    IntentCategory.B_DATABASE_ADMIN: {
        "persona": Persona.DBA,
        "skill_name": SkillName.ODOO_CRUD,
        "model": "anthropic/claude-3.5-sonnet",
    },
    IntentCategory.C_TESTING_QA: {
        "persona": Persona.QA,
        "skill_name": SkillName.MAGIC_FIX,
        "model": "anthropic/claude-3.5-sonnet",
    },
    IntentCategory.D_DOCUMENTATION: {
        "persona": Persona.DOCS,
        "skill_name": SkillName.ODOO_BUSINESS_ANALYST,
        "model": "meta-llama/llama-3.1-8b-instruct",
    },
    IntentCategory.E_RESEARCH: {
        "persona": Persona.SCOUT,
        "skill_name": None,
        "model": "anthropic/claude-3.5-sonnet",
    },
    IntentCategory.F_ARCHITECTURE: {
        "persona": Persona.ARCH,
        "skill_name": SkillName.ODOO_API_EXPERT,
        "model": "anthropic/claude-3.5-sonnet",
    },
    IntentCategory.G_PROJECT_MANAGEMENT: {
        "persona": Persona.PM,
        "skill_name": SkillName.ODOO_BUSINESS_ANALYST,
        "model": "meta-llama/llama-3.1-8b-instruct",
    },
    IntentCategory.H_GENERAL_CHAT: {
        "persona": Persona.GENERIC,
        "skill_name": None,
        "model": "meta-llama/llama-3.1-8b-instruct",
    },
}


class Dispatcher:
    """
    Dispatcher (Intent Router) odpowiedzialny za klasyfikację żądań i delegację do odpowiednich person.
    """

    def __init__(self, llm_client=None):
        """
        Zależność wstrzykiwana: llm_client. W produkcji to instancja klienta komunikującego się
        np. z OpenRouter dla Llama 3.1 8B. W testach można podać mock.
        """
        self.llm_client = llm_client

    def _build_prompt(self, message: str) -> str:
        return f"""Jesteś systemem klasyfikacji intencji dla zespołu agentów AI pracujących nad systemem Odoo.
Zklasyfikuj poniższą wiadomość przypisując ją do JEDNEJ z kategorii (A-H).

Kategorie:
A: Code_Generation (Pisanie kodu, bugfixy)
B: Database_Administration (SQL, migracje, RLS)
C: Testing_QA (Testy, Playwright, audyty bezpieczeństwa)
D: Documentation (Dokumentacja, README)
E: Research (Wyszukiwanie informacji, przegląd logów, czytanie bazy wiedzy)
F: Architecture (Projektowanie systemów, wzorce)
G: Project_Management (Zarządzanie taskami, statusy, raportowanie)
H: General_Chat (Inne, ogólna rozmowa)

Wiadomość użytkownika:
"{message}"

Zwróć TYLKO czysty JSON w następującym formacie:
{{"category": "A"}}
"""

    def classify_intent(self, message: str) -> DispatchResult:
        """
        Klasyfikuje intencję na podstawie wiadomości i zwraca obiekt DispatchResult.
        Jeśli llm_client nie jest dostarczony, używa prostego klasyfikatora na bazie heurystyk (fallback).
        """
        skill_name = None
        if self.llm_client:
            # W produkcji odpytujemy Llamę 3.1 8B (local inference lub OpenRouter)
            response_text = self.llm_client.chat(self._build_prompt(message))
            try:
                data = json.loads(response_text)
                category_val = data.get("category", "H")
                category = IntentCategory(category_val)
            except (json.JSONDecodeError, ValueError):
                category = IntentCategory.H_GENERAL_CHAT
        else:
            # Fallback (heurystyki do testów lub gdy brak dostępu do LLM)
            msg_lower = message.lower()
            if any(k in msg_lower for k in ["kod", "napisz", "bug", "fix", "code"]):
                category = IntentCategory.A_CODE_GENERATION
                skill_name = SkillName.ODOO_DEVELOPER
            elif any(k in msg_lower for k in ["import", "etl", "mass", "5000"]):
                category = IntentCategory.B_DATABASE_ADMIN
                skill_name = SkillName.ODOO_ETL_MANAGER
            elif any(k in msg_lower for k in ["baz", "sql", "tabel", "db", "migracj"]):
                category = IntentCategory.B_DATABASE_ADMIN
                skill_name = SkillName.ODOO_CRUD
            elif any(k in msg_lower for k in ["zmienił", "kto", "kiedy", "audit", "history"]):
                category = IntentCategory.E_RESEARCH
                skill_name = SkillName.ODOO_AUDIT_HISTORY
            elif any(k in msg_lower for k in ["security", "pii", "audyt", "bezpieczeństw"]):
                category = IntentCategory.C_TESTING_QA
                skill_name = SkillName.SECURITY_AUDIT
            elif any(k in msg_lower for k in ["test", "playwright", "qa", "sprawdź"]):
                category = IntentCategory.C_TESTING_QA
            elif any(k in msg_lower for k in ["architektura", "wzorzec", "hld"]):
                category = IntentCategory.F_ARCHITECTURE
                skill_name = SkillName.ODOO_API_EXPERT
            else:
                category = IntentCategory.H_GENERAL_CHAT

        route = ROUTING_TABLE[category]
        return DispatchResult(
            category=category,
            persona=Persona(route["persona"]) if route.get("persona") else None,
            skill_name=skill_name or route.get("skill_name"),
            recommended_model=str(route["model"]),
        )

    def forward_message(
        self, message: str, dispatch_result: DispatchResult
    ) -> Dict[str, Any]:
        """
        Wzorzec `forward_message` (eliminacja głuchego telefonu).
        Pakuje wiadomość i informacje o routingu, przesyłając oryginalną intencję dalej.
        """
        return {
            "original_message": message,
            "category": dispatch_result.category.value,
            "target_persona": dispatch_result.persona.value if dispatch_result.persona else None,
            "target_skill": dispatch_result.skill_name.value if dispatch_result.skill_name else None,
            "recommended_model": dispatch_result.recommended_model,
            "status": "routed",
        }
