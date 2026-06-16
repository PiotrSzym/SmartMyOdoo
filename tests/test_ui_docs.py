"""DOC-01: strażnik strukturalny Centrum Dokumentacji (statyczne checki plików UI)."""

from pathlib import Path

_UI = Path(__file__).resolve().parents[1] / "smartmyodoo" / "ui"
_INDEX = (_UI / "index.html").read_text(encoding="utf-8")
_DOCS = (_UI / "js" / "components" / "docs.js").read_text(encoding="utf-8")
_CANVAS = (_UI / "js" / "components" / "canvas.js").read_text(encoding="utf-8")


def test_docs_tab_and_screen_present():
    assert 'id="tab-docs"' in _INDEX
    assert 'id="docs-screen"' in _INDEX
    assert "js/components/docs.js" in _INDEX
    assert "key: 'docs'" in _CANVAS


def test_stale_modal_removed():
    """Dawny statyczny modal + funkcja usunięte (był nieaktualny port 5050)."""
    assert 'id="docs-modal"' not in _INDEX
    assert "function showDocsModal" not in _INDEX
    # poza komentarzem o usunięciu — żadnego funkcjonalnego 5050
    assert "localhost:5050" not in _INDEX
    assert "5050" not in _DOCS


def test_docs_has_all_sections_and_search():
    for sid in [
        "start",
        "arch",
        "sec",
        "vault",
        "models",
        "skills",
        "sprints",
        "kb",
    ]:
        assert f'id: "{sid}"' in _DOCS, f"brak sekcji {sid}"
    assert "docs-search" in _DOCS  # wyszukiwarka
    assert "Centrum Dokumentacji" in _DOCS
    assert "Kompendium wiedzy" in _DOCS


def test_docs_uses_correct_port():
    assert "127.0.0.1:8000" in _DOCS  # aktualny port serwera
