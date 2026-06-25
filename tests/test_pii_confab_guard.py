"""TRUST-01 T1: confab-guard PII w prompcie systemowym czatu.

Cel (US-T1, decyzja D1): model ZGADYWAŁ zamaskowane tokeny zamiast je cytować:
  'RMO <PERSON_2>'           -> model: 'RMO Billing Type'      (zmyślone)
  '<LOCATION_1> list…'       -> model: 'can list possibility'  (zmyślone)
Guard = instrukcja systemowa (nie post-processing): model NIE rozwija tokenów
typu <PERSON_x>/<LOCATION_x>/<ORG_x>/<..._x>, cytuje dosłownie albo mówi
"[zamaskowane]". Testujemy builder promptu — bez realnego LLM.
"""

from smartmyodoo.swarm.executor import SkillExecutor
from smartmyodoo.swarm.skills.skill_config import SkillConfig
from smartmyodoo.swarm.models import SkillName


def _config():
    return SkillConfig(
        name=SkillName.ODOO_CRUD,
        system_prompt="Bazowy prompt skilla.",
        allowed_tools=[],
        red_flags=[],
        recommended_model="test-model",
    )


def test_system_prompt_contains_confab_guard():
    executor = SkillExecutor()
    messages = executor._build_initial_messages(_config(), "ile zadań w rmo")
    assert messages[0]["role"] == "system"
    system = messages[0]["content"]
    # Zachowuje oryginalny prompt skilla...
    assert "Bazowy prompt skilla." in system
    # ...i dokłada twardą regułę confab-guard.
    assert "<PERSON_" in system
    # Wzmianka, że tokenów NIE wolno rozwijać/zgadywać (PL).
    low = system.lower()
    assert "nie" in low and ("zgad" in low or "rozwij" in low or "wymyśl" in low)


def test_confab_guard_mentions_token_families():
    executor = SkillExecutor()
    system = executor._build_initial_messages(_config(), "x")[0]["content"]
    for token in ("<PERSON_", "<LOCATION_", "<ORG"):
        assert token in system, f"guard pomija rodzinę tokenów {token}"


# TRUST-02 T1: guard jest VERBATIM-ONLY — model ma cytować token dosłownie,
# żeby deanonymize przywrócił prawdziwą wartość lokalnemu userowi.
def test_confab_guard_mandates_verbatim_echo():
    executor = SkillExecutor()
    system = executor._build_initial_messages(_config(), "x")[0]["content"]
    assert "DOSŁOWNIE" in system, "guard musi nakazywać cytowanie tokenu dosłownie"


# TRUST-02 T1: guard ZABRANIA podmiany tokenu na '[zamaskowane]' (blokuje deanonymize).
def test_confab_guard_forbids_zamaskowane_substitution():
    executor = SkillExecutor()
    low = executor._build_initial_messages(_config(), "x")[0]["content"].lower()
    assert "nie zastępuj" in low and "[zamaskowane]" in low, (
        "guard musi jawnie zakazać zastępowania tokenu zwrotem [zamaskowane]"
    )


# TRUST-02 T1 (US-T1a): zwykłe słowo/literówka bez formy <TYP_numer> NIE jest maską
# (regresja: model brał literówkę 'jkie' za zamaskowany token).
def test_confab_guard_says_plain_word_is_not_a_mask():
    executor = SkillExecutor()
    low = executor._build_initial_messages(_config(), "x")[0]["content"].lower()
    assert "nie jest maską" in low and "literówka" in low


def test_confab_guard_is_idempotent():
    # Dwukrotne złożenie promptu nie dubluje guarda (np. przy ponownym wywołaniu).
    executor = SkillExecutor()
    cfg = _config()
    s1 = executor._build_initial_messages(cfg, "a")[0]["content"]
    s2 = executor._build_initial_messages(cfg, "b")[0]["content"]
    assert s1.count("ZASADA DANYCH ZAMASKOWANYCH") == 1
    assert s1 == s2
