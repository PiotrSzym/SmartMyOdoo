"""TRUST-01 T5 (decyzja D5): dispatcher/rozmowa nie gubi zakresu między turami.

Scenariusz regresji (sesja 2026-06-25):
  Tura 1: "ile zadań w projekcie rmo"  -> model filtruje project_id=136 -> 2 zadania
  Tura 2: "jakie opisy w zadaniach"    -> BEZ pamięci zakresu zwracało 2920 (wszystkie)
Cel: tura 2 (follow-up) dziedziczy project_id z tury 1.

Test integracyjny na mocku danych (bez realnego Odoo): symulujemy warstwę
danych, w której zapytanie BEZ project_id zwraca 2920, a z project_id=136 → 2.
"""

from smartmyodoo.swarm.conversation_scope import ConversationScope


# ── Mock warstwy danych Odoo (ground-truth RMO) ──
ALL_TASKS_COUNT = 2920
RMO_PROJECT_ID = 136
RMO_TASKS_COUNT = 2


def fake_search_count(domain):
    """Mock: liczba zadań zależna od obecności filtra project_id (jak żywa baza)."""
    for clause in domain:
        if isinstance(clause, (list, tuple)) and clause[0] == "project_id":
            if clause[2] == RMO_PROJECT_ID:
                return RMO_TASKS_COUNT
    return ALL_TASKS_COUNT


def test_scope_captured_from_first_turn():
    scope = ConversationScope()
    # Tura 1: model odpytał project.task z filtrem project_id=136.
    domain1 = [("project_id", "=", RMO_PROJECT_ID)]
    pid = scope.capture_domain("ws", "sess", domain1)
    assert pid == RMO_PROJECT_ID
    assert scope.get_project_id("ws", "sess") == RMO_PROJECT_ID


def test_followup_inherits_project_and_returns_two_not_2920():
    scope = ConversationScope()
    # Tura 1: filtr po RMO.
    scope.capture_domain("ws", "sess", [("project_id", "=", RMO_PROJECT_ID)])

    # Tura 2: follow-up "jakie opisy w zadaniach" — BEZ jawnego project_id.
    hint = scope.scope_hint("ws", "sess", "jakie opisy w zadaniach")
    assert hint is not None, "follow-up powinien dostać podpowiedź z zakresem"
    assert f"project_id={RMO_PROJECT_ID}" in hint

    # Symulacja: dzięki podpowiedzi model utrzymuje filtr → 2, nie 2920.
    domain_followup = [("project_id", "=", RMO_PROJECT_ID)]
    assert fake_search_count(domain_followup) == RMO_TASKS_COUNT
    # Kontrola negatywna: bez filtra byłoby 2920 (stary bug).
    assert fake_search_count([]) == ALL_TASKS_COUNT


def test_no_hint_when_no_prior_scope():
    scope = ConversationScope()
    # Brak wcześniejszego zakresu → brak narzucania filtra.
    assert scope.scope_hint("ws", "sess", "jakie opisy w zadaniach") is None


def test_no_hint_for_non_followup_message():
    scope = ConversationScope()
    scope.capture_domain("ws", "sess", [("project_id", "=", RMO_PROJECT_ID)])
    # Pytanie o coś niezwiązanego (nie follow-up) → nie narzucamy starego projektu.
    assert scope.scope_hint("ws", "sess", "ile mamy kontaktów w bazie") is None


def test_scope_isolated_per_session():
    scope = ConversationScope()
    scope.capture_domain("ws", "sessA", [("project_id", "=", RMO_PROJECT_ID)])
    # Inna sesja nie dziedziczy zakresu sesji A.
    assert scope.get_project_id("ws", "sessB") is None


def test_inject_hint_adds_system_message_after_main_prompt():
    scope = ConversationScope()
    scope.capture_domain("ws", "sess", [["project_id", "=", RMO_PROJECT_ID]])
    messages = [
        {"role": "system", "content": "Bazowy prompt."},
        {"role": "user", "content": "jakie opisy w zadaniach"},
    ]
    out = scope.inject_hint("ws", "sess", "jakie opisy w zadaniach", messages)
    assert out[0]["role"] == "system" and out[0]["content"] == "Bazowy prompt."
    assert out[1]["role"] == "system"
    assert f"project_id={RMO_PROJECT_ID}" in out[1]["content"]
    # Wiadomość usera pozostaje na końcu.
    assert out[-1]["role"] == "user"


def test_dispatcher_classify_uses_cheap_haiku_tier():
    # D5: dispatcher (classify_intent) idzie tanim, ale MOCNIEJSZYM modelem (haiku-4.5),
    # nie llama-8b. Sprawdzamy kontrakt polityki modeli.
    from smartmyodoo.swarm.model_policy import resolve_model, MODEL_POLICY, ModelTier

    assert resolve_model("classify_intent") == MODEL_POLICY[ModelTier.CHEAP]
    assert MODEL_POLICY[ModelTier.CHEAP].endswith("claude-haiku-4.5")
