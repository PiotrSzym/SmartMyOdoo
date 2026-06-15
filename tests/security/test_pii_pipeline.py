"""S1.1 (dowód): PII jest pseudonimizowane na ścieżce czat/pipeline (SkillExecutor).

PRZED naprawą: `SkillExecutor` wysyłał surową wiadomość użytkownika i wyniki narzędzi
wprost do LLM (`executor.py` linie ~88/181) — wyciek danych klientów mimo deklaracji RODO.
PO naprawie: executor anonimizuje przed LLM i deanonimizuje dla użytkownika (round-trip).
"""

import json

from smartmyodoo.mcp.pii_middleware import PiiMiddleware
from smartmyodoo.swarm.executor import SkillExecutor
from smartmyodoo.swarm.models import SkillName
from smartmyodoo.swarm.skills.skill_config import SkillConfig


class _Msg:
    def __init__(self, content):
        self.role = "assistant"
        self.content = content
        self.tool_calls = None


class _Choice:
    def __init__(self, content):
        self.message = _Msg(content)


class _Resp:
    def __init__(self, content):
        self.choices = [_Choice(content)]


class _EchoLLM:
    """Odsyła pseudonimizowaną wiadomość użytkownika jako odpowiedź (do testu round-tripu)."""

    def __init__(self):
        self.seen_messages = None

    def chat(self, messages, tools=None):
        self.seen_messages = messages
        anon_user = messages[-1]["content"]
        return _Resp(f"Potwierdzam: {anon_user}")


def _skill():
    return SkillConfig(
        name=SkillName.ODOO_DEVELOPER,
        system_prompt="Jesteś asystentem Odoo.",
        allowed_tools=[],
        red_flags=[],
        recommended_model="claude-3-5-sonnet",
    )


def test_pii_not_sent_to_llm_and_deanonymized_for_user():
    pii = PiiMiddleware()
    llm = _EchoLLM()
    ex = SkillExecutor(llm_client=llm, pii=pii, workspace_id="w_test")

    # Wiadomość z realnym PII: nazwisko + PESEL
    msg = "Wystaw fakturę dla Jan Kowalski, PESEL 44051401458"
    result = ex.execute(_skill(), msg)

    # 1) Do LLM NIE trafiło surowe PII
    sent = json.dumps(llm.seen_messages, ensure_ascii=False)
    assert "44051401458" not in sent, "PESEL wyciekł do LLM!"
    assert "Kowalski" not in sent, "Nazwisko wyciekło do LLM!"
    # ...zamiast tego są tokeny pseudonimizacji
    assert (
        "<" in sent and "_" in sent
    ), "Brak tokenów pseudonimizacji w payloadzie do LLM"

    # 2) Użytkownik dostaje REALNE dane (deanonimizacja po stronie wyjścia)
    assert "44051401458" in result["response"], "Odpowiedź nie zdeanonimizowana (PESEL)"
    assert "Kowalski" in result["response"], "Odpowiedź nie zdeanonimizowana (nazwisko)"


def test_no_pii_middleware_is_noop():
    """Bez PiiMiddleware executor działa jak dawniej (kompatybilność wsteczna)."""
    llm = _EchoLLM()
    ex = SkillExecutor(llm_client=llm, pii=None, workspace_id="w_test")
    result = ex.execute(_skill(), "Zwykła wiadomość bez PII")
    assert "Zwykła wiadomość bez PII" in result["response"]
