"""TRUST-03 T3 (Summary Buffer): last-N tur dosłownie + streszczenie starszych tur.

Wzorzec produkcyjny rynku: gdy rozmowa przekracza okno, starsze tury → JEDNO
syntetyczne streszczenie (oznaczone), ostatnie N tur zostaje dosłownie. Streszczenie
deterministyczne (ekstraktywne) — zero dodatkowego wywołania LLM.
"""

from smartmyodoo.core.chat_repository import ChatRepository


def _repo_with(messages):
    repo = ChatRepository.__new__(ChatRepository)
    repo.get_session_messages = lambda session_id, limit=600: messages  # type: ignore
    return repo


def _convo(n_pairs):
    out = []
    for i in range(n_pairs):
        out.append({"role": "user", "content": f"pytanie {i}"})
        out.append({"role": "assistant", "content": f"odpowiedź {i}"})
    return out


def test_no_summary_when_within_window():
    # 2 tury, okno = 6 → brak streszczenia, tylko okno dosłowne.
    hist = _repo_with(_convo(2)).get_history_context("s", max_turns=6)
    assert all(not m.get("synthetic") for m in hist)
    assert len(hist) == 4  # 2 pary


def test_summary_added_when_history_exceeds_window():
    # 10 tur, okno = 3 → starsze (7 tur) streszczone, ostatnie 3 dosłowne.
    hist = _repo_with(_convo(10)).get_history_context("s", max_turns=3)
    # pierwszy element = syntetyczne streszczenie
    assert hist[0]["role"] == "system" and hist[0].get("synthetic") is True
    assert "STRESZCZENIE" in hist[0]["content"]
    # ostatnie 3 tury dosłownie (6 wiadomości)
    window = [m for m in hist if not m.get("synthetic")]
    assert len(window) == 6
    assert window[-1] == {"role": "assistant", "content": "odpowiedź 9"}


def test_summary_contains_older_user_questions():
    hist = _repo_with(_convo(10)).get_history_context("s", max_turns=3)
    summary = hist[0]["content"]
    # streszczenie niesie wcześniejsze pytania usera (gist), np. „pytanie 0"
    assert "pytanie 0" in summary
    # ...ale NIE te z okna (ostatnie 3 tury: pytanie 7,8,9)
    assert "pytanie 8" not in summary


def test_window_content_truncated_in_history():
    msgs = [
        {"role": "user", "content": "u"},
        {"role": "assistant", "content": "y" * 5000},
    ]
    hist = _repo_with(msgs).get_history_context("s", max_turns=6, max_chars=2000)
    long = [m for m in hist if m["role"] == "assistant"][0]
    assert len(long["content"]) <= 2000 + 10 and long["content"].endswith("[…]")


def test_empty_when_no_convo():
    assert _repo_with([]).get_history_context("s", max_turns=6) == []
