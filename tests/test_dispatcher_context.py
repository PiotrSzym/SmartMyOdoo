"""TRUST-01 T5 / TRUST-03 T4: pamięć zakresu rozmowy (capture project_id) + tier.

Po TRUST-03 T4 plaster `scope_hint`/`inject_hint` został USUNIĘTY (zastąpiony przez
`context_block` T2 + deterministyczny `enforce_scope` T2 — testy w
`test_entity_memory.py` i `test_scope_enforce.py`). Tu zostają niezmienne kontrakty:
przechwytywanie project_id, izolacja per sesja oraz tier dispatchera.

Ground-truth: RMO=136, 2 zadania (vs 2920 globalnie).
"""

from smartmyodoo.swarm.conversation_scope import ConversationScope

RMO_PROJECT_ID = 136


def test_scope_captured_from_first_turn():
    scope = ConversationScope()
    pid = scope.capture_domain("ws", "sess", [("project_id", "=", RMO_PROJECT_ID)])
    assert pid == RMO_PROJECT_ID
    assert scope.get_project_id("ws", "sess") == RMO_PROJECT_ID


def test_scope_isolated_per_session():
    scope = ConversationScope()
    scope.capture_domain("ws", "sessA", [("project_id", "=", RMO_PROJECT_ID)])
    # Inna sesja nie dziedziczy zakresu sesji A.
    assert scope.get_project_id("ws", "sessB") is None


def test_clear_resets_scope_and_records():
    scope = ConversationScope()
    scope.capture_domain("ws", "sess", [("project_id", "=", RMO_PROJECT_ID)])
    scope.capture_records("ws", "sess", "project.task", [{"id": 6706, "name": "X"}])
    scope.clear("ws", "sess")
    assert scope.get_project_id("ws", "sess") is None
    assert scope.context_block("ws", "sess") is None


def test_dispatcher_classify_uses_cheap_haiku_tier():
    # D5: dispatcher (classify_intent) idzie tanim, ale MOCNIEJSZYM modelem (haiku-4.5).
    from smartmyodoo.swarm.model_policy import resolve_model, MODEL_POLICY, ModelTier

    assert resolve_model("classify_intent") == MODEL_POLICY[ModelTier.CHEAP]
    assert MODEL_POLICY[ModelTier.CHEAP].endswith("claude-haiku-4.5")
