import unittest
from unittest.mock import MagicMock, patch
import json
import sys


# Mock odoo module
class DummyController(object):
    pass


odoo_mock = MagicMock()
http_mock = MagicMock()
http_mock.Controller = DummyController
http_mock.route = lambda *args, **kwargs: lambda f: f

sys.modules["odoo"] = odoo_mock
sys.modules["odoo.http"] = http_mock

# Po zmockowaniu możemy bezpiecznie importować kontroler
from ..controllers.main import FirefliesWebhook


class TestFirefliesWebhook(unittest.TestCase):
    def setUp(self):
        super(TestFirefliesWebhook, self).setUp()
        self.controller = FirefliesWebhook()
        self.mock_request = MagicMock()
        self.mock_env = MagicMock()
        self.mock_request.env = self.mock_env
        self.mock_env[
            "ir.config_parameter"
        ].sudo().get_param.return_value = "TEST_TOKEN"

        self.mock_crm_lead = MagicMock()
        self.mock_env["crm.lead"].sudo.return_value = self.mock_crm_lead

    @patch("odoo.addons.fireflies_connector.controllers.main.request")
    def test_webhook_unauthorized(self, patched_request):
        patched_request.env = self.mock_env
        patched_request.httprequest.headers = {}

        response = self.controller.fireflies_webhook()

        self.assertEqual(response.status_code, 401)
        data = json.loads(response.data.decode("utf-8"))
        self.assertEqual(data.get("error"), "Unauthorized")

    @patch("odoo.addons.fireflies_connector.controllers.main.request")
    def test_webhook_authorized_success(self, patched_request):
        patched_request.env = self.mock_env
        patched_request.httprequest.headers = {"Authorization": "Bearer TEST_TOKEN"}
        patched_request.httprequest.data = json.dumps(
            {
                "title": "Test meeting",
                "transcript": "Hello World",
                "attendees": ["test@example.com"],
            }
        ).encode("utf-8")

        response = self.controller.fireflies_webhook()

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode("utf-8"))
        self.assertEqual(data.get("status"), "ok")
        self.mock_crm_lead.process_fireflies_transcript.assert_called_once()

    @patch("odoo.addons.fireflies_connector.controllers.main.request")
    def test_webhook_malformed_json(self, patched_request):
        patched_request.env = self.mock_env
        patched_request.httprequest.headers = {"Authorization": "Bearer TEST_TOKEN"}
        patched_request.httprequest.data = b"NOT_A_JSON"

        response = self.controller.fireflies_webhook()

        self.assertEqual(response.status_code, 500)
        data = json.loads(response.data.decode("utf-8"))
        self.assertIn("error", data)
