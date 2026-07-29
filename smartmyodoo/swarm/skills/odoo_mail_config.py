from smartmyodoo.swarm.models import SkillName
from smartmyodoo.swarm.skills.skill_config import SkillConfig

skill = SkillConfig(
    name=SkillName.ODOO_MAIL_CONFIG,
    system_prompt=(
        "Konfiguracja poczty Odoo: nadawca (email_from), serwery wychodzące "
        "(ir.mail_server, from_filter), aliasy (mail.alias), serwery przychodzące "
        "(fetchmail.server), automatyzacje (base.automation / ir.actions.server).\n"
        "ZASADY TWARDE:\n"
        "1) from_filter serwera MUSI pasować do adresu nadawcy — inaczej Odoo 17/18 "
        "(strict) przepisze nagłówek From na dozwolony adres. Przy zmianie nadawcy przypnij "
        "jawnie mail_server_id serwera, którego from_filter zawiera docelowy adres.\n"
        "2) NIE zmieniaj reply_to — to on wątkuje odpowiedzi do rekordu (alias projektu / "
        "catchall@). Przekierowanie reply_to na skrzynkę, której Odoo NIE pobiera (brak "
        "fetchmail / nie catchall) = odpowiedzi giną lub bounce.\n"
        "3) Wymuszenie nadawcy PER MODUŁ (np. Projekty): base.automation na mail.mail, "
        "trigger on_create (nie on_create_or_write), akcja Python przepisująca email_from "
        "tylko dla docelowych model (np. project.task/project.project), z ochroną adresów "
        "szablonowych (Field Service serwis@) i idempotencją.\n"
        "4) TEST BEZPIECZNY zamiast realnej wysyłki: utwórz mail.mail ze state='cancel', "
        "sprawdź email_from po regule, potem unlink — nic nie wychodzi.\n"
        "5) Powiadomienia do userów WEWNĘTRZNYCH idą in-app (Discuss), nie mailem — nie "
        "tworzą mail.mail. Realny test wysyłki = przypisanie zadania ('Zostałeś przydzielony').\n"
        "Zawsze rób backup wartości przed zmianą i informuj, że zmiany są odwracalne "
        "(dezaktywacja reguły / przywrócenie alias_name)."
    ),
    allowed_tools=[
        "odoo_search",
        "odoo_schema",
        "odoo_update",
        "odoo_create",
        "read_odoo_log",
        "search_knowledge_base",
    ],
    red_flags=[
        "never_break_reply_to",
        "require_from_filter_match",
        "protect_template_sender",
    ],
    requires_shadow_mode=False,
    requires_human_override=False,
    recommended_model="claude-3-5-sonnet",
)
