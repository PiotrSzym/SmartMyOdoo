"""TRUST-03 T2 (Entity Memory + disambiguacja): jawna kotwica encji.

/qa LIVE: „dodaj do opisu price list" trafiało w model `product.pricelist` (cennik)
zamiast w zadanie „Price list possibility". T2 zapamiętuje POKAZANE rekordy (id+tytuł)
i wstrzykuje blok kontekstu z regułą „preferuj pokazany rekord nad modelem o tej
samej nazwie" — deterministyczne uzupełnienie historii (T1).

Ground-truth: RMO=136; zadania 6706 „Price list possibility", 6862 „Audtyt…".
"""

from smartmyodoo.swarm.conversation_scope import ConversationScope

RMO = 136
RECORDS = [
    {"id": 6862, "name": "Audtyt Hinduskich modułów"},
    {"id": 6706, "name": "Price list possibility"},
]


def _scoped():
    s = ConversationScope()
    s.capture_domain("ws", "sess", [("project_id", "=", RMO)])
    s.capture_records("ws", "sess", "project.task", RECORDS)
    return s


def test_capture_records_stores_id_and_title():
    s = _scoped()
    block = s.context_block("ws", "sess")
    assert "id=6706" in block and "Price list possibility" in block
    assert "id=6862" in block


def test_context_block_has_disambiguation_rule():
    block = _scoped().context_block("ws", "sess")
    low = block.lower()
    assert "product.pricelist" in low  # reguła wymienia kolizyjny model
    assert "preferuj" in low or "tego rekordu" in low or "nie do" in low
    assert "project_id=136" in block  # aktywny projekt


def test_records_deduped_by_model_and_id():
    s = _scoped()
    # ponowne pokazanie tego samego zadania nie dubluje wpisu
    s.capture_records("ws", "sess", "project.task", [{"id": 6706, "name": "Price list possibility"}])
    block = s.context_block("ws", "sess")
    assert block.count("id=6706") == 1


def test_records_reset_on_project_change():
    s = _scoped()
    assert "6706" in s.context_block("ws", "sess")
    # Zmiana projektu → kotwica rekordów wyzerowana (US-T2b)
    s.capture_domain("ws", "sess", [("project_id", "=", 999)])
    block = s.context_block("ws", "sess")
    assert "6706" not in block  # stare rekordy zniknęły
    assert "project_id=999" in block  # nowy projekt aktywny


def test_no_block_when_nothing_to_anchor():
    s = ConversationScope()
    assert s.context_block("ws", "sess") is None


def test_records_capped_to_last_8():
    s = ConversationScope()
    s.capture_domain("ws", "sess", [("project_id", "=", RMO)])
    many = [{"id": i, "name": f"task{i}"} for i in range(20)]
    s.capture_records("ws", "sess", "project.task", many)
    block = s.context_block("ws", "sess")
    # tylko ostatnie 8 (id 12..19)
    assert "id=19" in block and "id=12" in block
    assert "id=11" not in block


# ── Integracja z budową promptu ──
def test_context_block_injected_into_prompt():
    from smartmyodoo.swarm.executor import SkillExecutor
    from smartmyodoo.swarm.skills.skill_config import SkillConfig
    from smartmyodoo.swarm.models import SkillName

    ex = SkillExecutor()
    ex.pii = None
    ex.scope = _scoped()
    ex.chat_repo = None
    ex.workspace_id = "ws"
    ex.session_id = "sess"
    cfg = SkillConfig(
        name=SkillName.ODOO_CRUD, system_prompt="Bazowy.",
        allowed_tools=[], red_flags=[], recommended_model="m",
    )
    msgs = ex._build_initial_messages(cfg, "dodaj do opisu price list")
    joined = " ".join(m["content"] for m in msgs)
    assert "AKTYWNY KONTEKST" in joined and "Price list possibility" in joined
    assert "product.pricelist" in joined  # reguła disambiguacji w prompcie
