from smartmyodoo.swarm.models import IntentCategory, Persona
from smartmyodoo.swarm.dispatcher import Dispatcher


class MockLLMClient:
    def __init__(self, response_text: str):
        self.response_text = response_text

    def chat(self, prompt: str) -> str:
        return self.response_text


def test_dispatcher_fallback_heuristics():
    dispatcher = Dispatcher()

    # Test heurystyki Code
    res_code = dispatcher.classify_intent("napisz mi funkcję do logowania")
    assert res_code.category == IntentCategory.A_CODE_GENERATION
    assert res_code.persona == Persona.DEV

    # Test heurystyki DB
    res_db = dispatcher.classify_intent("zrób migrację bazy danych")
    assert res_db.category == IntentCategory.B_DATABASE_ADMIN
    assert res_db.persona == Persona.DBA

    # Test heurystyki Architektury
    res_arch = dispatcher.classify_intent(
        "jaka powinna być architektura dla tego modułu?"
    )
    assert res_arch.category == IntentCategory.F_ARCHITECTURE
    assert res_arch.persona == Persona.ARCH


def test_dispatcher_llm_classification():
    # Mock LLM zwracający poprawny JSON
    mock_client = MockLLMClient('{"category": "G"}')
    dispatcher = Dispatcher(llm_client=mock_client)

    res = dispatcher.classify_intent("Zaktualizuj status w Jira na Done")

    assert res.category == IntentCategory.G_PROJECT_MANAGEMENT
    assert res.persona == Persona.PM
    assert res.recommended_model == "meta-llama/llama-3.1-8b-instruct"


def test_dispatcher_llm_invalid_json():
    # Mock LLM zwracający zepsuty JSON (powinno zadziałać zabezpieczenie i fallback na H)
    mock_client = MockLLMClient("to nie jest json")
    dispatcher = Dispatcher(llm_client=mock_client)

    res = dispatcher.classify_intent("Hej, co słychać?")

    assert res.category == IntentCategory.H_GENERAL_CHAT
    assert res.persona == Persona.GENERIC


def test_forward_message():
    dispatcher = Dispatcher()
    original_msg = "Zrób testy dla logowania"

    res = dispatcher.classify_intent(original_msg)
    forwarded = dispatcher.forward_message(original_msg, res)

    assert forwarded["original_message"] == original_msg
    assert forwarded["category"] == "C"
    assert forwarded["target_persona"] == "Quality Assurance"
    assert forwarded["status"] == "routed"
    assert "recommended_model" in forwarded
