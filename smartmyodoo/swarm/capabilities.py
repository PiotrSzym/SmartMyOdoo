"""SELFDOC-01: wiarygodny self-opis czatu — z PRAWDZIWEGO rejestru, bez improwizacji.

Problem (zrzut usera): na „co potrafisz?" model wyliczał narzędzia z pamięci JEDNEGO
aktywnego skilla (niekompletnie, konfabulował). Tu budujemy opis DETERMINISTYCZNIE z
`SKILL_REGISTRY` (tylko realnie zarejestrowane skille) — zero zmyślania (motyw TRUST).
"""

from __future__ import annotations

import re

from smartmyodoo.swarm.skills.registry import SKILL_REGISTRY

# Kompaktowy opis per skill (ikona + 1 linia zdolności). Klucz = SkillName.value.
# Pełne tooltipy (z przykładami) żyją w /api/skills (panel UI). Tu — zwięźle do self-opisu.
SKILL_DESC = {
    "ODOO_BUSINESS_ANALYST": ("📊", "Business Analyst", "analiza biznesowa i konfiguracja Standard Odoo (bez kodu)"),
    "ODOO_DEVELOPER": ("💻", "Developer", "kod modułów przez `_inherit`, ORM, zero modyfikacji core"),
    "ODOO_DEVOPS_GITHUB": ("🚀", "DevOps/GitHub", "repozytorium, gałęzie, CI/CD, izolacja staging"),
    "ODOO_SH_LOGS": ("📋", "SH Logs", "diagnostyka logów i tracebacków (metoda bottom-up)"),
    "ODOO_AUDIT_HISTORY": ("🔍", "Audit History", "kto/co/kiedy zmienił (chatter → mail.message)"),
    "ODOO_CRUD": ("🗄️", "CRUD", "operacje na danych i relacjach (Magic Tuples (0,0,{}))"),
    "ODOO_ETL_MANAGER": ("📦", "ETL Manager", "masowe importy/migracje ze stronicowaniem"),
    "FINANCIAL_AUDIT": ("💰", "Financial Audit", "audyt księgowy: Lock Dates, noty kredytowe"),
    "SECURITY_AUDIT": ("🔒", "Security Audit", "bezpieczeństwo i RODO/PII, Record Rules"),
    "ODOO_API_EXPERT": ("🔌", "API Expert", "integracje XML-RPC/JSON-RPC/REST, API Keys"),
    "MAGIC_FIX": ("🪄", "Magic Fix", "operacje ratunkowe (force unlock, odblokowanie cronów)"),
}

# Pytania o możliwości (PL+EN). Świadomie wąskie — bez bare „pomoc/help" (false-positive).
_SELF_DESCRIBE_RE = re.compile(
    r"(co\s+(po)?trafisz|co\s+umiesz|do\s+czego\s+(jeste|służysz)|"
    r"jakie\s+(masz\s+)?(umiej|funkcj|skill|możliwo)|opowiedz\s+o\s+sobie|"
    r"przedstaw\s+się|kim\s+jesteś|twoje\s+(możliwo|umiej|skill|funkcj)|"
    r"what\s+can\s+you\s+do|who\s+are\s+you|introduce\s+yourself|your\s+(capabilit|skill))",
    re.IGNORECASE,
)


def is_self_describe_query(message: str) -> bool:
    """Czy wiadomość pyta o możliwości/tożsamość asystenta."""
    return bool(message and _SELF_DESCRIBE_RE.search(message))


def build_capabilities() -> str:
    """Zbuduj WIARYGODNY self-opis z rejestru (tylko realnie zarejestrowane skille)."""
    parts = [
        "## 🤖 Jestem SmartMyOdoo",
        "Asystent AI do Twojego ERP **Odoo** — rój wyspecjalizowanych ekspertów z "
        "bezpiecznym dostępem do danych (brama FastAPI, szyfrowany Skarbiec, "
        "pseudonimizacja PII, pamięć rozmowy).",
        "",
        "### 🧩 Moi eksperci (skille)",
    ]
    # Anty-konfabulacja: iterujemy WYŁĄCZNIE realnie zarejestrowane skille.
    for sn in SKILL_REGISTRY:
        icon, name, desc = SKILL_DESC.get(sn.value, ("🛠️", sn.value, ""))
        parts.append(f"- {icon} **{name}** — {desc}")

    parts += [
        "",
        "### 🛡️ Jak działam bezpiecznie",
        "- **Tylko-odczyt domyślnie** (🟢) — pytania o dane NIE zmieniają Odoo.",
        "- **Zapis przez propozycje** (Shadow Mode) — realna zmiana wymaga trybu 🔴 + PIN.",
        "- **Pseudonimizacja PII** — nazwiska/dane wrażliwe maskowane przed wysłaniem do chmury.",
        "- **Multi-Workspace** — wiele przestrzeni (każda z własnym Odoo i pamięcią).",
        "",
        "### ✅ Co mogę zrobić",
        "- **Czytać** dane Odoo: szanse CRM, zadania, kontakty, faktury, projekty.",
        "- **Rozpoznawać osoby** po nazwisku (serwerowo) i pamiętać kontekst rozmowy.",
        "- **Zapisywać** (tworzyć/edytować/usuwać rekordy) — w trybie 🔴 z PIN.",
        "- Diagnozować logi, audytować historię zmian, importować masowo, pisać kod modułów.",
        "",
        "Zapytaj wprost, np. *„ile szans w CRM\"*, *„edytuj nazwę zadania X\"*, "
        "*„kto zmienił fakturę\"*.",
    ]
    return "\n".join(parts)
