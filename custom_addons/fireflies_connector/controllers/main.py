import json
import logging
from odoo import http
from odoo.http import request, Response

logger = logging.getLogger(__name__)


class FirefliesWebhook(http.Controller):
    @http.route(
        "/api/fireflies/webhook",
        type="http",
        auth="public",
        methods=["POST"],
        csrf=False,
    )
    def fireflies_webhook(self, **post):
        """
        Publiczny endpoint dla webhooków z Fireflies AI.
        Omija mechanizm JSON-RPC. Wymaga weryfikacji nagłówka (Authorization).
        """
        try:
            # Pobranie oczekiwanego tokenu z ir.config_parameter z fallbackiem na hardcoded w razie braku konfiguracji
            expected_token = (
                request.env["ir.config_parameter"]
                .sudo()
                .get_param(
                    "smart_my_odoo.fireflies_webhook_token",
                    "SMART_MY_ODOO_SECURE_TOKEN",
                )
            )

            auth_header = request.httprequest.headers.get("Authorization")
            if not auth_header or auth_header != f"Bearer {expected_token}":
                return Response(
                    json.dumps({"error": "Unauthorized"}),
                    status=401,
                    mimetype="application/json",
                )

            # Fireflies przesyla JSON w body requestu
            raw_data = request.httprequest.data
            payload = json.loads(raw_data.decode("utf-8"))

            logger.info(
                f"Odebrano webhook od Fireflies: {payload.get('title', 'Brak tytulu')}"
            )

            # Przekazanie do modelu z podniesionymi uprawnieniami (sudo) poniewaz webhook jest auth='public'
            request.env["crm.lead"].sudo().process_fireflies_transcript(payload)

            return Response(
                json.dumps({"status": "ok"}), status=200, mimetype="application/json"
            )

        except Exception as e:
            logger.error(f"Błąd przetwarzania webhooka Fireflies: {str(e)}")
            return Response(
                json.dumps({"error": str(e)}), status=500, mimetype="application/json"
            )
