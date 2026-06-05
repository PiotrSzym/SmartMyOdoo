from odoo import http
from odoo.http import request
import requests  # type: ignore
import logging

_logger = logging.getLogger(__name__)


class SmartChatProxy(http.Controller):
    @http.route("/smart_chat/send", type="json", auth="user", methods=["POST"])
    def send_to_fastapi(self, **kwargs):
        """
        Proxy endpoint that receives JSON from the OWL frontend and forwards it to FastAPI.
        """
        # Get fields from OWL
        message = kwargs.get("message", "")
        active_model = kwargs.get("active_model")
        active_id = kwargs.get("active_id")
        session_id = kwargs.get("session_id", "default_session")
        user_id = request.env.user.id

        payload = {
            "message": message,
            "user_id": user_id,
            "active_model": active_model,
            "active_id": active_id,
            "session_id": session_id,
        }

        try:
            # Forward to FastAPI
            fastapi_url = "http://127.0.0.1:8000/api/chat"
            response = requests.post(fastapi_url, json=payload, timeout=5)
            response.raise_for_status()

            # Return JSON from FastAPI to the OWL frontend
            return response.json()

        except requests.exceptions.RequestException as e:
            _logger.error(f"SmartChat Proxy Error: {str(e)}")
            return {
                "reply": "Błąd komunikacji z silnikiem SmartMyOdoo (FastAPI niedostępne).",
                "action_type": "ERROR",
            }
