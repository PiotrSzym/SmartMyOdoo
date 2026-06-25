from smartmyodoo.swarm.models import SkillName
from smartmyodoo.swarm.skills.skill_config import SkillConfig

skill = SkillConfig(
    name=SkillName.ODOO_CRUD,
    system_prompt="Magic Tuples (0,0,{}) for One2many",
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
    red_flags=["no_delete_posted_invoice"],
    requires_shadow_mode=True,
    recommended_model="claude-3-5-sonnet",
)
