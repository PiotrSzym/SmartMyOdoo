"""T3 (WIRE-01) — Guard: żaden skill z SKILL_REGISTRY nie może być osierocony.

Dla KAŻDEGO `SkillName` zarejestrowanego w `SKILL_REGISTRY` musi istnieć
przynajmniej jedno wejście użytkownika, dla którego `Dispatcher.classify_intent`
zwraca ten właśnie skill. „Wejście" to albo intencja tekstowa (ścieżka fallback
heurystyk), albo wymuszona kategoria klasyfikatora LLM (ścieżka ROUTING_TABLE) —
obie są legalnymi drogami routingu w produkcji.

Test FAIL-uje, gdy skill istnieje w rejestrze, ale dispatcher nigdy go nie wybiera
(regres „martwego kodu", US-WIRE-3).
"""

import pytest

from smartmyodoo.swarm.dispatcher import Dispatcher
from smartmyodoo.swarm.models import SkillName
from smartmyodoo.swarm.skills.registry import SKILL_REGISTRY


class _Msg:
    def __init__(self, content):
        self.role = "assistant"
        self.content = content


class _Choice:
    def __init__(self, content):
        self.message = _Msg(content)


class _Resp:
    def __init__(self, content):
        self.choices = [_Choice(content)]


class _CategoryLLM:
    """Mock LLM wymuszający konkretną kategorię (A-H) — zgodny z kontraktem chat(messages)."""

    def __init__(self, category_letter: str):
        self._category = category_letter

    def chat(self, messages, tools=None):
        return _Resp(f'{{"category": "{self._category}"}}')


# Probe = (intencja_tekstowa, kategoria_LLM | None).
# - Jeśli kategoria_LLM is None → ścieżka fallback heurystyk (Dispatcher() bez llm_client).
# - Jeśli podana → ścieżka klasyfikatora LLM (Dispatcher(llm_client=_CategoryLLM(...))).
# Wymóg twardy: KAŻDY SkillName w SKILL_REGISTRY ma tu wpis prowadzący do niego.
PROBES: dict[SkillName, tuple[str, str | None]] = {
    SkillName.ODOO_DEVELOPER: ("napisz kod nowego modułu", None),
    SkillName.ODOO_CRUD: ("zmień rekord w bazie przez sql", None),
    SkillName.ODOO_ETL_MANAGER: ("zaimportuj 5000 produktów (etl)", None),
    SkillName.ODOO_AUDIT_HISTORY: ("kto i kiedy zmienił ten rekord", None),
    SkillName.SECURITY_AUDIT: ("zrób audyt security i pii", None),
    SkillName.ODOO_API_EXPERT: ("zaprojektuj architekturę i wzorzec integracji", None),
    SkillName.MAGIC_FIX: ("uruchom test playwright", None),
    # Osiągalny wyłącznie przez ROUTING_TABLE (kategoria D/G → BA), nie przez fallback.
    SkillName.ODOO_BUSINESS_ANALYST: ("zaktualizuj status zadania", "G"),
    # --- Trzy skile, które przed T1 są OSIEROCONE (RED) ---
    SkillName.ODOO_SH_LOGS: ("pokaż ostatnie logi i traceback wyjątku", None),
    SkillName.FINANCIAL_AUDIT: ("sprawdź faktury i księgowość VAT, zapis", None),
    SkillName.ODOO_DEVOPS_GITHUB: (
        "zrób deploy na branch staging github odoo.sh push",
        None,
    ),
}


def _resolve(probe: tuple[str, str | None]) -> SkillName | None:
    text, category = probe
    if category is None:
        dispatcher = Dispatcher()
    else:
        dispatcher = Dispatcher(llm_client=_CategoryLLM(category))
    return dispatcher.classify_intent(text).skill_name


def test_every_registered_skill_has_a_probe():
    """Sanity: tabela PROBES pokrywa cały SKILL_REGISTRY (inaczej guard ma martwe pola)."""
    missing = set(SKILL_REGISTRY.keys()) - set(PROBES.keys())
    assert not missing, f"Brak probe dla skili w PROBES: {sorted(s.value for s in missing)}"


@pytest.mark.parametrize("skill_name", list(SKILL_REGISTRY.keys()), ids=lambda s: s.value)
def test_skill_is_reachable_from_dispatcher(skill_name: SkillName):
    """Każdy skill z rejestru musi być osiągalny przez ≥1 wejście (US-WIRE-3)."""
    probe = PROBES[skill_name]
    got = _resolve(probe)
    assert got == skill_name, (
        f"Skill {skill_name.value} jest OSIEROCONY: dispatcher dla probe "
        f"{probe!r} zwrócił {got.value if got else None}, oczekiwano {skill_name.value}. "
        f"Dodaj ścieżkę routingu (fallback/ROUTING_TABLE) w swarm/dispatcher.py."
    )


def test_no_orphaned_skills_overall():
    """Agregat: zbiór osiągalnych skili == cały SKILL_REGISTRY (zero osieroconych)."""
    reachable = {s for s in SKILL_REGISTRY if _resolve(PROBES[s]) == s}
    orphaned = set(SKILL_REGISTRY.keys()) - reachable
    assert not orphaned, (
        "Osierocone skile (w rejestrze, nieosiągalne z dispatchera): "
        f"{sorted(s.value for s in orphaned)}"
    )


# --------------------------------------------------------------------------- #
# T3-NEG (WIRE-01/US-WIRE-3, dodane przez /qa) — META-test guardu.
#
# Dowodzi, że guard NIE jest tautologią: gdy routing sztucznie „osieroci" skill
# zarejestrowany w SKILL_REGISTRY (regres — dispatcher przestaje go zwracać),
# logika guardu MUSI wykryć osierocenie (RED). Bez tego case'a guard pozytywny
# mógłby zielenić się nawet po realnym regresie routingu.
# --------------------------------------------------------------------------- #


def test_guard_red_when_skill_artificially_orphaned(monkeypatch):
    """Sztucznie osieracamy jeden skill (dispatcher przestaje go zwracać) →
    agregat guardu MUSI wykryć go jako osierocony (assert wewnątrz guardu pada)."""
    victim = SkillName.ODOO_SH_LOGS  # dowolny realnie routowalny skill
    assert _resolve(PROBES[victim]) == victim, (
        "Pre-condition: skill-ofiara musi być osiągalny PRZED osieroceniem."
    )

    real_classify = Dispatcher.classify_intent

    def crippled_classify(self, message: str):
        result = real_classify(self, message)
        # Symulacja regresu: dispatcher „gubi" jeden skill (zwraca None zamiast niego).
        if result.skill_name == victim:
            result = result.model_copy(update={"skill_name": None})
        return result

    monkeypatch.setattr(Dispatcher, "classify_intent", crippled_classify)

    # Powtarzamy logikę agregatu guardu na okaleczonym dispatcherze.
    reachable = {s for s in SKILL_REGISTRY if _resolve(PROBES[s]) == s}
    orphaned = set(SKILL_REGISTRY.keys()) - reachable

    # Guard MUSI teraz uznać `victim` za osierocony — inaczej jest ślepy na regres.
    assert victim in orphaned, (
        f"META-test guardu zawiódł: po sztucznym osieroceniu {victim.value} "
        f"guard NIE wykrył regresu (orphaned={sorted(s.value for s in orphaned)}). "
        "Guard jest tautologiczny / nieczuły na regres routingu."
    )

    # Po cofnięciu monkeypatch (koniec testu) guard znów musi być zielony —
    # weryfikuje to oddzielny test pozytywny `test_no_orphaned_skills_overall`.
