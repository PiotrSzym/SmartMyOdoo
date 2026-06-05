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
            # Autoryzacja po tokenie w naglowku (Hardcoded dla przykladu, normalnie w odoo.conf lub ir.config_parameter)
            auth_header = request.httprequest.headers.get("Authorization")
            if not auth_header or auth_header != "Bearer SMART_MY_ODOO_SECURE_TOKEN":
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
