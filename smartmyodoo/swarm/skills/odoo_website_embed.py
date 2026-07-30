from smartmyodoo.swarm.models import SkillName
from smartmyodoo.swarm.skills.skill_config import SkillConfig

skill = SkillConfig(
    name=SkillName.ODOO_WEBSITE_EMBED,
    system_prompt=(
        "Osadzanie SAMODZIELNEGO pliku HTML+JS (deck szkoleniowy, mini-SPA, prezentacja) "
        "w Odoo jako strona Website — BEZ wgrywania custom modułu, wyłącznie rekordy ORM.\n"
        "ZASADY TWARDE:\n"
        "1) NIE wklejaj samodzielnego dokumentu (własny <head>, reset CSS, inline JS) do "
        "edytora Website (buildera) — konflikt z Bootstrap/motywem Odoo, wygląd się rozjeżdża.\n"
        "2) NIE serwuj go surowo przez /web/content/<att> jako src iframe — Odoo nakłada tam "
        "'Content-Security-Policy: default-src \\'none\\'' + X-Content-Type-Options: nosniff, "
        "co BLOKUJE inline <script> i <style> → martwy, nieostylowany szkielet.\n"
        "3) Custom moduł-kontroler (http.route) jest NIEWYKONALNY na Odoo SaaS (.odoo.com — "
        "brak dostępu do filesystemu/gita; db-manager Access Denied). Odoo.sh wymaga repo+build. "
        "Domyślnie zakładaj tylko dostęp XML-RPC/ORM.\n"
        "4) DZIAŁAJĄCY WZORZEC (3 rekordy): strony Website NIE mają CSP, więc:\n"
        "   a) ir.attachment: mimetype='text/html', public=False (tylko zalogowani → anon 404), "
        "company_id=False (multi-company: czyta każdy zalogowany pracownik dowolnej firmy; "
        "dostęp egzekwuje ir.attachment.check() w Pythonie, nie ir.rule).\n"
        "   b) ir.ui.view (qweb, website_id=<id>): standalone <html> BEZ t-call='website.layout' "
        "(brak chrome/asset injection), pełnoekranowy <iframe id=deck> + loader JS: "
        "fetch('/web/content/<att>',{credentials:'same-origin'}).then(r=>r.text())"
        ".then(t=>{iframe.srcdoc=t}).\n"
        "   c) website.page: url, view_id, website_id, visibility='connected' (=tylko zalogowani, "
        "egzekwowane w PageController), is_published=True, website_indexed=False.\n"
        "5) KLUCZ: wstrzykuj HTML do iframe przez PRZYPISANIE property .srcdoc w JS — NIGDY jako "
        "atrybut srcdoc w arch XML (parser zwija \\n→spacja i psuje //-komentarze JS). srcdoc "
        "dziedziczy CSP rodzica (brak) → inline JS/CSS decka działa.\n"
        "6) Podmiana treści = nadpisanie pola 'datas' (base64) tego samego załącznika — URL bez "
        "zmian. SCORM/Scrum niepotrzebne, jeśli deck ma własny silnik quizów.\n"
        "Zawsze weryfikuj po wdrożeniu: anon → strona 403 i /web/content 404 (brama), zalogowany "
        "→ strona 200 bez CSP i /web/content 200 z bajtami decka. Uwaga na multi-company przy "
        "doborze company_id/website_id."
    ),
    allowed_tools=[
        "odoo_search",
        "odoo_schema",
        "odoo_create",
        "odoo_update",
        "search_knowledge_base",
    ],
    red_flags=[
        "never_serve_js_via_web_content_csp",
        "attachment_company_id_false_multicompany",
        "no_custom_module_on_saas",
        "srcdoc_via_dom_property_not_xml_attr",
    ],
    requires_shadow_mode=False,
    requires_human_override=False,
    recommended_model="claude-3-5-sonnet",
)
