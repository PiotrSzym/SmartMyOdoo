from smartmyodoo.swarm.models import SkillName
from smartmyodoo.swarm.skills.skill_config import SkillConfig

skill = SkillConfig(
    name=SkillName.ODOO_AUDIT_HISTORY,
    system_prompt="Chatter tracking via mail.message",
    allowed_tools=[
        "odoo_search",
        "resolve_person",
        "odoo_schema",
        "odoo_create",
        "odoo_update",
        "odoo_delete",
        "search_knowledge_base",
        "scaffold_module",
        "read_odoo_log",
        "search_odoo_code",
    ],
    red_flags=[],
    read_only=True,
    recommended_model="claude-3-5-sonnet",
)
