from smartmyodoo.swarm.models import SkillName
from smartmyodoo.swarm.skills.skill_config import SkillConfig

skill = SkillConfig(
    name=SkillName.ODOO_SH_LOGS,
    system_prompt="Tracebacki bottom-up, rozróżniaj logi aplikacji vs deployment",
    allowed_tools=[
        "odoo_search",
        "resolve_person",
        "odoo_schema",
        "odoo_create",
        "search_knowledge_base",
        "scaffold_module",
        "read_odoo_log",
        "search_odoo_code",
    ],
    red_flags=[],
    recommended_model="claude-3-5-sonnet",
)
