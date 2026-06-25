"""TRUST-03 T1 (Buffer Window): odtwarzanie ostatnich N tur BIEŻĄCEJ sesji do LLM.

Dziś LLM nie dostawał historii bieżącej sesji (get_smart_context pomija ją) — stąd
gubienie kontekstu („price list" → cennik). Tu testujemy, że okno historii:
- bierze tylko user/assistant (pomija duże 'tool'),
- ogranicza liczbę tur i przycina długie treści (budżet),
- jest wstrzykiwane do promptu PRZED bieżącą wiadomością.
"""

from smartmyodoo.core.chat_repository import ChatRepository
from smartmyodoo.swarm.executor import SkillExecutor
from smartmyodoo.swarm.skills.skill_config import SkillConfig
from smartmyodoo.swarm.models import SkillName


def _repo_with(messages):
    # Ominięcie __init__/DB — testujemy czystą logikę okna.
    repo = ChatRepository.__new__(ChatRepository)
    repo.get_session_messages = lambda session_id, limit=400: messages  # type: ignore
    return repo


def test_window_filters_tool_and_caps_turns():
    msgs = []
    for i in range(10):
        msgs.append({"role": "user", "content": f"u{i}"})
        msgs.append({"role": "tool", "content": "BIG ODOO DUMP " * 100})
        msgs.append({"role": "assistant", "content": f"a{i}"})
    win = _repo_with(msgs).get_recent_window("s", max_turns=2)
    assert all(m["role"] in ("user", "assistant") for m in win)  # 'tool' pominięte
    assert len(win) <= 4  # ≈ 2 tury (para user+assistant)
    assert win[-1] == {"role": "assistant", "content": "a9"}  # najnowsze na końcu


def test_window_truncates_long_content():
    win = _repo_with([{"role": "assistant", "content": "x" * 5000}]).get_recent_window(
        "s", max_turns=6, max_chars=2000
    )
    assert len(win[0]["content"]) <= 2000 + 10
    assert win[0]["content"].endswith("[…]")


def test_window_empty_when_zero_turns():
    assert _repo_with([{"role": "user", "content": "u"}]).get_recent_window(
        "s", max_turns=0
    ) == []


# ── Integracja z budową promptu ──
def _config():
    return SkillConfig(
        name=SkillName.ODOO_CRUD,
        system_prompt="Bazowy.",
        allowed_tools=[],
        red_flags=[],
        recommended_model="test-model",
    )


class _FakeRepo:
    def __init__(self, window):
        self._w = window

    def get_smart_context(self, ws, sid):
        return []

    def get_history_context(self, sid, max_turns=6):
        return self._w

    def save_message(self, *a, **k):
        pass


def test_build_initial_messages_includes_current_session_history():
    ex = SkillExecutor()
    ex.pii = None  # _anon = tożsamość (czytelna asercja)
    ex.scope = None
    ex.workspace_id = "ws"
    ex.session_id = "s"
    ex.chat_repo = _FakeRepo(
        [
            {"role": "user", "content": "jakie zadania w rmo"},
            {"role": "assistant", "content": "Zadania: Price list possibility (6706)"},
        ]
    )
    msgs = ex._build_initial_messages(_config(), "dodaj do opisu price list")

    # Historia bieżącej sesji trafiła do kontekstu...
    assert any(
        m["role"] == "assistant" and "Price list possibility" in m["content"]
        for m in msgs
    ), "okno historii bieżącej sesji nie zostało wstrzyknięte"
    # ...i poprzedza bieżącą wiadomość użytkownika (ostatnia).
    assert msgs[-1] == {"role": "user", "content": "dodaj do opisu price list"}
