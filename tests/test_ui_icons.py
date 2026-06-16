"""ADR-006: ikony UI z jednego źródła (icons.js) — guard."""

from pathlib import Path

_UI = Path(__file__).resolve().parents[1] / "smartmyodoo" / "ui"
_ICONS = (_UI / "js" / "icons.js").read_text(encoding="utf-8")
_SKILLS = (_UI / "js" / "components" / "skills.js").read_text(encoding="utf-8")
_INDEX = (_UI / "index.html").read_text(encoding="utf-8")

_SKILL_IDS = [
    "ODOO_BUSINESS_ANALYST",
    "ODOO_DEVELOPER",
    "ODOO_DEVOPS_GITHUB",
    "ODOO_SH_LOGS",
    "ODOO_AUDIT_HISTORY",
    "ODOO_CRUD",
    "ODOO_ETL_MANAGER",
    "FINANCIAL_AUDIT",
    "SECURITY_AUDIT",
    "ODOO_API_EXPERT",
    "MAGIC_FIX",
]


def test_icons_single_source_has_all_skills():
    assert "SKILL_ICONS" in _ICONS and "PROGRAM_ICONS" in _ICONS
    for sid in _SKILL_IDS:
        assert f"{sid}:" in _ICONS, f"brak ikony dla {sid} w icons.js"
    for pid in ["P1", "P2", "P3", "P4", "P5"]:
        assert f"{pid}:" in _ICONS, f"brak ikony programu {pid}"


def test_icons_js_loaded_before_components():
    assert "js/icons.js" in _INDEX
    # icons.js przed skills.js (kolejność ładowania)
    assert _INDEX.index("js/icons.js") < _INDEX.index("js/components/skills.js")


def test_skills_panel_uses_single_source_icons():
    assert "window.skillIcon(" in _SKILLS  # agenci z icons.js
    assert "window.programIcon(" in _SKILLS  # programy z icons.js
    assert "createIcons" in _SKILLS  # render Lucide po przebudowie
