from unittest.mock import MagicMock
from smartmyodoo.swarm.recon import EnvironmentRecon


def test_detect_version():
    client_mock = MagicMock()
    client_mock.version.return_value = {"server_version": "18.0"}
    client_mock.url = "https://mycompany.odoo.com"

    recon = EnvironmentRecon(client_mock)
    info = recon.detect_version()

    assert info.odoo_version == "18.0"


def test_classify_hosting():
    client_mock = MagicMock()

    client_mock.url = "https://mycompany.odoo.com"
    recon = EnvironmentRecon(client_mock)
    assert recon.classify_hosting(client_mock.url) == "saas"

    client_mock.url = "https://mycompany.odoo.sh"
    recon = EnvironmentRecon(client_mock)
    assert recon.classify_hosting(client_mock.url) == "odoo_sh"

    client_mock.url = "https://erp.mycompany.pl"
    recon = EnvironmentRecon(client_mock)
    assert recon.classify_hosting(client_mock.url) == "on_premise"


def test_detect_version_connection_error():
    client_mock = MagicMock()
    client_mock.version.side_effect = ConnectionError("Cannot connect to Odoo")
    client_mock.url = "https://mycompany.odoo.com"

    recon = EnvironmentRecon(client_mock)
    info = recon.detect_version()

    assert info.odoo_version == "unknown"
    assert info.hosting_type == "unknown"
    assert info.edition == "unknown"


def test_detect_edition_enterprise():
    client_mock = MagicMock()
    client_mock.search_read.return_value = [{"license": "OEEL-1"}]

    recon = EnvironmentRecon(client_mock)
    assert recon.detect_edition() == "enterprise"


def test_detect_edition_community():
    client_mock = MagicMock()
    # Brak zainstalowanego modułu (lub licencja inna)
    client_mock.search_read.return_value = [{"license": "LGPL-3"}]

    recon = EnvironmentRecon(client_mock)
    assert recon.detect_edition() == "community"


def test_detect_edition_empty_result():
    client_mock = MagicMock()
    # Błąd zapytania lub brak dostępu
    client_mock.search_read.return_value = []

    recon = EnvironmentRecon(client_mock)
    assert recon.detect_edition() == "community"
