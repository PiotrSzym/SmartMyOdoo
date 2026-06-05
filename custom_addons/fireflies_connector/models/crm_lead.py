import logging
from odoo import models, api

logger = logging.getLogger(__name__)


class CrmLead(models.Model):
    _inherit = "crm.lead"

    @api.model
    def process_fireflies_transcript(self, payload):
        """
        Główna funkcja wywoływana przez webhook Fireflies.
        Implementuje 4-krokowy algorytm dopasowywania klienta.
        """
        # Przyklad budowy payloadu z Fireflies:
        # { "title": "...", "transcript": "...", "attendees": ["jdoe@example.com"] }

        attendees = payload.get("attendees", [])
        transcript = payload.get("transcript", "")
        title = payload.get("title", "")

        matched_partner = False

        # KROK 1: Email
        for email in attendees:
            partner = self.env["res.partner"].search([("email", "=", email)], limit=1)
            if partner:
                matched_partner = partner
                break

        # KROK 2: Domena
        if not matched_partner:
            for email in attendees:
                if "@" in email:
                    domain = email.split("@")[1]
                    # Ignorujemy domeny publiczne (gmail, hotmail)
                    if domain not in ["gmail.com", "yahoo.com", "hotmail.com"]:
                        partner = self.env["res.partner"].search(
                            [("email", "ilike", f"@{domain}")], limit=1
                        )
                        if partner:
                            matched_partner = partner
                            break

        # KROK 3 & 4 (Uproszczone dla prototypu - wymaga np. wywołania AI w celu weryfikacji nazw)

        # Jeśli znaleziono partnera - dopnij notatkę do Leada, jeśli istnieje, lub utwórz nowego
        if matched_partner:
            lead = self.search([("partner_id", "=", matched_partner.id)], limit=1)
            if not lead:
                lead = self.create(
                    {
                        "name": f"Spotkanie z Fireflies: {title}",
                        "partner_id": matched_partner.id,
                    }
                )

            # Wrzuca transkrypcje w Chatter
            lead.message_post(
                body=f"<b>Transkrypcja ze spotkania:</b><br/>{transcript}"
            )
            logger.info(f"Przypisano transkrypcje do Leada ID: {lead.id}")
        else:
            logger.warning(
                "Nie dopasowano żadnego partnera dla transkrypcji Fireflies."
            )
            # W domysle - utworz leada "Unassigned" lub zglos do weryfikacji manualnej
            self.create(
                {
                    "name": f"[Nieprzypisane] Spotkanie Fireflies: {title}",
                    "description": transcript,
                }
            )
