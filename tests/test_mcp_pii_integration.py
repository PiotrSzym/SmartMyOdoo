import os
import json
from unittest.mock import patch, MagicMock
from smartmyodoo.mcp.server import search_odoo_records, create_odoo_record


@patch("smartmyodoo.mcp.server.get_odoo_client")
@patch("smartmyodoo.mcp.server.shadow_mode.create_proposal")
def test_mcp_pii_integration_roundtrip(mock_create_proposal, mock_get_client):
    os.environ["PII_ENABLED_TESTWS"] = "True"

    mock_client = MagicMock()
    mock_client.search_read.return_value = [
        {"id": 1, "name": "Jan Kowalski", "vat": "1234563218"}
    ]
    mock_get_client.return_value = mock_client

    # 1. Search - powinno zanonimizować dane wychodzące do agenta
    result = search_odoo_records(model_name="res.partner", workspace_id="testws")

    assert isinstance(result, dict)

    records = result.get("records", [])
    assert len(records) == 1

    anonymized_name = records[0]["name"]
    anonymized_vat = records[0]["vat"]

    assert "Jan" not in anonymized_name
    assert "<PERSON" in anonymized_name

    assert "1234563218" not in anonymized_vat
    assert "<NIP" in anonymized_vat

    # 2. Create - powinno zdeanonimizować dane przychodzące od agenta
    values_json = json.dumps({"name": anonymized_name, "vat": anonymized_vat})
    reason = f"Dodano {anonymized_name}"

    mock_create_proposal.return_value = {"id": 999}

    response = create_odoo_record(
        "res.partner", values_json, reason, workspace_id="testws"
    )
    assert "999" in response

    args, kwargs = mock_create_proposal.call_args
    assert "Jan Kowalski" in args[3]["name"]
    assert "1234563218" in args[3]["vat"]
    assert "Jan Kowalski" in args[4]
