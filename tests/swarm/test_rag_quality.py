"""FIX-02 S5.3: jakość RAG — chunking z overlapem + sygnalizacja degradacji (bez fabrykacji)."""

from unittest.mock import Mock, patch

from smartmyodoo.swarm.brain.rag_api import SharedBrain, DEGRADED_MSG


def _brain_with_mock_store(store):
    with patch("smartmyodoo.swarm.brain.rag_api.LanceDBClient", return_value=store):
        return SharedBrain()


def test_chunks_have_overlap():
    """Tekst > 1 chunk → sąsiednie chunki współdzielą ogon (overlap)."""
    brain = _brain_with_mock_store(Mock(degraded=False))
    sentences = [f"Zdanie numer {i} z pewną treścią." for i in range(60)]
    text = " ".join(sentences)

    chunks = brain._chunk_text(text, max_length=300, overlap=80)
    assert len(chunks) > 1
    # dla każdej pary sąsiednich chunków istnieje wspólny fragment (overlap)
    for a, b in zip(chunks, chunks[1:]):
        tail = a[-40:]
        assert tail in b or any(
            w in b for w in tail.split() if len(w) > 3
        ), "brak overlapu między sąsiednimi chunkami"


def test_chunks_respect_max_length():
    brain = _brain_with_mock_store(Mock(degraded=False))
    text = " ".join(f"Krótkie zdanie {i}." for i in range(100))
    chunks = brain._chunk_text(text, max_length=200, overlap=50)
    assert all(len(c) <= 200 for c in chunks)


def test_long_single_sentence_hard_split():
    brain = _brain_with_mock_store(Mock(degraded=False))
    text = "x" * 1000  # jedno "zdanie" bez granic
    chunks = brain._chunk_text(text, max_length=300, overlap=50)
    assert len(chunks) > 1
    assert all(len(c) <= 300 for c in chunks)


def test_degraded_signals_not_fabricates():
    """Mock/degradacja → flaga degraded=True + jawny komunikat, NIE zmyślony kontekst."""
    store = Mock()
    store.degraded = True
    store.search.return_value = []  # po S5.3 mock nie fabrykuje
    brain = _brain_with_mock_store(store)

    res = brain.retrieve("cokolwiek")
    assert res["degraded"] is True
    assert res["hits"] == 0
    assert res["context"] == DEGRADED_MSG
    assert "Mocked RAG response" not in res["context"]
    # ask_brain (str) też zwraca jawny komunikat degradacji
    assert brain.ask_brain("cokolwiek") == DEGRADED_MSG


def test_healthy_retrieval_reports_hits():
    store = Mock()
    store.degraded = False
    store.search.return_value = [
        {"text": "Treść A", "source": "a.md"},
        {"text": "Treść B", "source": "b.md"},
    ]
    brain = _brain_with_mock_store(store)
    res = brain.retrieve("pytanie")
    assert res["degraded"] is False
    assert res["hits"] == 2
    assert "Treść A" in res["context"] and "b.md" in res["context"]
