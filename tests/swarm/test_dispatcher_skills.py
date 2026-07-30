from smartmyodoo.swarm.dispatcher import Dispatcher
from smartmyodoo.swarm.models import IntentCategory, SkillName


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
    """Mock LLM wymuszający konkretną kategorię (A-H) — kontrakt chat(messages)."""

    def __init__(self, category_letter: str):
        self._category = category_letter

    def chat(self, messages, tools=None):
        return _Resp(f'{{"category": "{self._category}"}}')


def test_dispatcher_etl_manager():
    dispatcher = Dispatcher()
    result = dispatcher.classify_intent("Zaimportuj 5000 produktów do bazy")
    assert result.skill_name == SkillName.ODOO_ETL_MANAGER


# --------------------------------------------------------------------------- #
# WIRE-02 — routing w ścieżce LLM: klasyfikator LLM daje ZGRUBNĄ kategorię
# (A-H), a deterministyczny router słów kluczowych DOPRECYZOWUJE skill wewnątrz
# niej. Dowód, że skile o wąskim zastosowaniu (mail/website) są osiągalne także
# w produkcji z LLM, nie tylko w fallbacku heurystyk.
# --------------------------------------------------------------------------- #


def test_dispatcher_llm_specializes_mail_config():
    d = Dispatcher(llm_client=_CategoryLLM("B"))
    r = d.classify_intent("zmień nadawcę maili wychodzących z modułu projekty")
    assert r.skill_name == SkillName.ODOO_MAIL_CONFIG


def test_dispatcher_llm_specializes_website_embed():
    d = Dispatcher(llm_client=_CategoryLLM("F"))
    r = d.classify_intent("osadź szkolenie jako stronę website w odoo")
    assert r.skill_name == SkillName.ODOO_WEBSITE_EMBED


def test_dispatcher_llm_category_overrides_heuristic_but_skill_survives():
    """Kategoria z LLM nadpisuje heurystyczną, ale skill ze słów kluczowych zostaje."""
    d = Dispatcher(llm_client=_CategoryLLM("A"))
    r = d.classify_intent("zmień nadawcę maili wychodzących z modułu projekty")
    # Persona/kategoria wg LLM (A), ale skill doprecyzowany słowami kluczowymi.
    assert r.category == IntentCategory.A_CODE_GENERATION
    assert r.skill_name == SkillName.ODOO_MAIL_CONFIG


def test_dispatcher_audit_history():
    dispatcher = Dispatcher()
    result = dispatcher.classify_intent("Sprawdź kto zmienił fakturę i kiedy")
    assert result.skill_name == SkillName.ODOO_AUDIT_HISTORY


def test_dispatcher_security():
    dispatcher = Dispatcher()
    result = dispatcher.classify_intent(
        "Zrób audyt PII i security dla modelu res.partner"
    )
    assert result.skill_name == SkillName.SECURITY_AUDIT
