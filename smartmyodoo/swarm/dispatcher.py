from typing import Any, Dict

import json

from .models import DispatchResult, IntentCategory, Persona, SkillName
from .model_policy import resolve_model

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
        # WIRE-01 (D1/T1): E_RESEARCH obejmuje „przegląd logów" (patrz _build_prompt).
        # Domyślny skill dla researchu logów = ODOO_SH_LOGS, zamiast osieroconego None.
        # Fallback heurystyk nadal może nadpisać to bardziej specyficznym skilem
        # (np. ODOO_AUDIT_HISTORY dla „kto/kiedy") — final_skill = skill_name or route.
        "skill_name": SkillName.ODOO_SH_LOGS,
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
            # S2.1: poprawny kontrakt — chat() przyjmuje messages=[...] i zwraca OBIEKT odpowiedzi,
            # nie string. Wcześniej chat(str) → None → json.loads(None) → TypeError (crash).
            response = self.llm_client.chat(
                messages=[{"role": "user", "content": self._build_prompt(message)}]
            )
            response_text = ""
            if response is not None and getattr(response, "choices", None):
                response_text = response.choices[0].message.content or ""
            try:
                data = json.loads(response_text)
                category_val = data.get("category", "H")
                category = IntentCategory(category_val)
            except (json.JSONDecodeError, ValueError, TypeError):
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
            elif any(
                k in msg_lower for k in ["zmienił", "kto", "kiedy", "audit", "history"]
            ):
                category = IntentCategory.E_RESEARCH
                skill_name = SkillName.ODOO_AUDIT_HISTORY
            elif any(
                k in msg_lower for k in ["security", "pii", "audyt", "bezpieczeństw"]
            ):
                category = IntentCategory.C_TESTING_QA
                skill_name = SkillName.SECURITY_AUDIT
            # --- WIRE-01 (D1/T1): podpięcie 3 osieroconych skili z SKILL_REGISTRY ---
            # Kolejność CELOWA: po `audyt/security` i `kto/kiedy` (te nie mogą być
            # kanibalizowane), przed generycznym `test`. „odoo.sh" sprowadzone do
            # `odoo_sh` przez `.` → spacja w msg_lower jest niezmienione, dlatego
            # matchujemy zarówno wariant z kropką, jak i frazę „odoo sh".
            elif any(
                k in msg_lower
                for k in ["deploy", "branch", "staging", "github", "odoo.sh", "odoo sh", "push"]
            ):
                # DevOps/CI Odoo.sh (deploy, gałęzie, staging) — przed gałęzią logów,
                # bo „błąd deploy" diagnozujemy z logów, ale samo „deploy/branch/push"
                # to operacja DevOps.
                category = IntentCategory.F_ARCHITECTURE
                skill_name = SkillName.ODOO_DEVOPS_GITHUB
            elif any(
                k in msg_lower
                for k in ["logi", "logu", "logó", "loga", "logach", "traceback", "stacktrace"]
            ):
                # Diagnostyka logów/tracebacków → ODOO_SH_LOGS (E_RESEARCH).
                # Świadomie NIE matchujemy bare „log", bo łapie „logowanie/zalogować"
                # (false positive, kanibalizował test C_TESTING_QA „testy dla logowania").
                category = IntentCategory.E_RESEARCH
                skill_name = SkillName.ODOO_SH_LOGS
            elif any(
                k in msg_lower
                for k in ["faktur", "księgow", "ksiegow", "vat", "zaksięgow", "zaksiegow", "journal"]
            ):
                # Audyt księgowy (faktury/VAT/zapisy księgowe) → FINANCIAL_AUDIT.
                # UWAGA: po `kto/kiedy` (ODOO_AUDIT_HISTORY), więc „kto zmienił fakturę"
                # nadal trafia do historii zmian, nie do audytu księgowego.
                category = IntentCategory.E_RESEARCH
                skill_name = SkillName.FINANCIAL_AUDIT
            elif any(
                k in msg_lower
                for k in [
                    "alias", "smtp", "nadawc", "email_from", "serwer poczt",
                    "skrzynk", "reply-to", "reply_to", "z jakiego adresu",
                    "wychodzą maile", "wychodza maile", "wychodzą powiadom", "adres wysył",
                ]
            ):
                # Konfiguracja poczty Odoo (serwery wych./przych., aliasy, nadawca per
                # moduł) → ODOO_MAIL_CONFIG. CELOWO przed „test" (bo bywa „sprawdź adres…")
                # i po księgowości (żeby „faktura na maila" nie kanibalizowała).
                category = IntentCategory.B_DATABASE_ADMIN
                skill_name = SkillName.ODOO_MAIL_CONFIG
            elif any(
                k in msg_lower
                for k in [
                    "osadź stron", "osadzić stron", "osadź szkol", "osadz html",
                    "hostuj html", "hostować html", "wgraj html", "standalone html",
                    "website page", "stronę website", "strona website", "iframe",
                    "srcdoc", "szkolenie w odoo", "prezentacj w odoo", "deck w odoo",
                ]
            ):
                # Osadzanie samodzielnego HTML+JS (deck/SPA) jako strona Website Odoo
                # (ir.attachment + qweb view + website.page, srcdoc). CELOWO przed „test",
                # bo bywa „sprawdź stronę…", i po poczcie (żeby „strona z mailem" nie
                # kanibalizowała).
                category = IntentCategory.B_DATABASE_ADMIN
                skill_name = SkillName.ODOO_WEBSITE_EMBED
            elif any(k in msg_lower for k in ["test", "playwright", "qa", "sprawdź"]):
                category = IntentCategory.C_TESTING_QA
            elif any(k in msg_lower for k in ["architektura", "wzorzec", "hld"]):
                category = IntentCategory.F_ARCHITECTURE
                skill_name = SkillName.ODOO_API_EXPERT
            else:
                category = IntentCategory.H_GENERAL_CHAT

        route = ROUTING_TABLE[category]
        final_skill = skill_name or route.get("skill_name")
        # K4: model dobierany po POZIOMIE skilla (tani↔drogi), nie sztywno z ROUTING_TABLE
        recommended_model = resolve_model(final_skill.value if final_skill else None)
        return DispatchResult(
            category=category,
            persona=Persona(route["persona"]) if route.get("persona") else None,
            skill_name=final_skill,
            recommended_model=recommended_model,
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
            "target_persona": dispatch_result.persona.value
            if dispatch_result.persona
            else None,
            "target_skill": dispatch_result.skill_name.value
            if dispatch_result.skill_name
            else None,
            "recommended_model": dispatch_result.recommended_model,
            "status": "routed",
        }
