from smartmyodoo.swarm.models import SkillName
from smartmyodoo.swarm.skills.skill_config import SkillConfig

skill = SkillConfig(
    name=SkillName.ODOO_DEVELOPER,
    system_prompt="_inherit mandatory, no core modification",
    allowed_tools=[
        "odoo_search",
        "odoo_schema",
        "odoo_create",
        "search_knowledge_base",
        "scaffold_module",
        "read_odoo_log",
        "search_odoo_code",
    ],
    red_flags=["no_core_mod", "no_uninstall_base_module"],
    requires_shadow_mode=True,
    recommended_model="claude-3-5-sonnet",
)
