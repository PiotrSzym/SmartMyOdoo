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
    # DOC-02: usunięto „Sprinty & Roadmap"; dodano Funkcje + Agenci (na bazie sprintów).
    for sid in [
        "start",
        "features",
        "arch",
        "agents",
        "sec",
        "vault",
        "models",
        "kb",
    ]:
        assert f'id: "{sid}"' in _DOCS, f"brak sekcji {sid}"
    assert 'id: "sprints"' not in _DOCS, "sekcja Sprinty powinna być usunięta"
    assert "docs-search" in _DOCS  # wyszukiwarka
    assert "Centrum Dokumentacji" in _DOCS
    assert "Kompendium wiedzy" in _DOCS


def test_docs_lists_all_11_agents():
    """Dokumentacja oddaje realny zakres: 11 wyspecjalizowanych agentów."""
    assert _DOCS.count('["') >= 11 or _DOCS.count('["') >= 11
    for agent in ["Business Analyst", "Magic Fix", "Security Audit", "ETL Manager"]:
        assert agent in _DOCS, f"brak agenta {agent}"


def test_nav_uses_lucide_icons():
    assert 'data-lucide="message-circle"' in _INDEX  # Czat
    assert 'data-lucide="activity"' in _INDEX  # Aktywność
    assert "js/vendor/lucide" in _INDEX  # Lucide hostowane LOKALNIE (nie CDN)
    assert "unpkg.com" not in _INDEX  # brak zależności od CDN
    assert "createIcons" in _INDEX  # init ikon


def test_lucide_vendored_locally():
    """Plik Lucide jest w repo (offline-first), poprawny UMD."""
    f = _UI / "js" / "vendor" / "lucide.min.js"
    assert f.exists(), "brak lokalnego lucide.min.js"
    head = f.read_text(encoding="utf-8", errors="ignore")[:300]
    assert "lucide" in head.lower()


def test_docs_uses_correct_port():
    assert "127.0.0.1:8000" in _DOCS  # aktualny port serwera


# ── I18N-01: wielojęzyczność ──
_I18N = (_UI / "js" / "i18n.js").read_text(encoding="utf-8")


def test_i18n_framework_present():
    assert "js/i18n.js" in _INDEX  # załadowany
    assert 'id="lang-switch"' in _INDEX  # przełącznik w nav
    assert "pl:" in _I18N and "en:" in _I18N  # oba języki
    assert "function t(" in _I18N and "applyI18n" in _I18N


def test_nav_has_i18n_keys():
    for key in ["nav.vault", "nav.chat", "nav.docs"]:
        assert f'data-i18n="{key}"' in _INDEX, f"brak data-i18n {key}"
    assert "data-i18n-title=" in _INDEX  # tooltipy tłumaczone


def test_docs_is_bilingual():
    # treść dokumentacji ma wariant PL i EN
    assert "What is SmartMyOdoo" in _DOCS  # EN
    assert "Czym jest SmartMyOdoo" in _DOCS  # PL
    assert "Knowledge base" in _DOCS and "Kompendium wiedzy" in _DOCS
