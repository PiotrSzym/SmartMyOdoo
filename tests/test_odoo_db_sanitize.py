"""Sanitizer nazwy bazy Odoo — ucina etykietę Odoo.sh `[branch/version]` (pułapka)."""

from pathlib import Path

from smartmyodoo.core.odoo_connector import sanitize_db_name


def test_strips_odoo_sh_label():
    assert (
        sanitize_db_name("myodoo-pl-myodoopl-master-6970793 [production/16.0]")
        == "myodoo-pl-myodoopl-master-6970793"
    )


def test_strips_label_and_whitespace():
    assert sanitize_db_name("  prod-db  ") == "prod-db"
    assert sanitize_db_name("db [staging/17.0]") == "db"


def test_keeps_clean_name():
    assert sanitize_db_name("ps-myodoo-test-main") == "ps-myodoo-test-main"


def test_handles_empty():
    assert sanitize_db_name("") == ""
    assert sanitize_db_name(None) is None


def test_connector_applies_sanitizer():
    """OdooProjectConnector czyści nazwę bazy w ścieżce połączenia."""
    src = (
        Path(__file__).resolve().parents[1]
        / "smartmyodoo"
        / "core"
        / "odoo_connector.py"
    ).read_text(encoding="utf-8")
    assert "sanitize_db_name(credentials.get(" in src
