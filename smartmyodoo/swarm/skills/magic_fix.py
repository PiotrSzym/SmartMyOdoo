from smartmyodoo.swarm.models import SkillName
from smartmyodoo.swarm.skills.skill_config import SkillConfig

skill = SkillConfig(
    name=SkillName.MAGIC_FIX,
    system_prompt="Force unlock, omijanie ORM tylko w sytuacji kryzysowej",
    allowed_tools=["odoo_search", "odoo_schema", "odoo_create", "search_knowledge_base", "scaffold_module", "read_odoo_log", "search_odoo_code"],
    red_flags=["no_drop_table", "no_truncate"],
    requires_human_override=True,
    requires_shadow_mode=True,
    recommended_model="claude-3-5-sonnet",
)
