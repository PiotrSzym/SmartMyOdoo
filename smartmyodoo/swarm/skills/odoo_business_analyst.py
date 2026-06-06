from smartmyodoo.swarm.models import SkillName
from smartmyodoo.swarm.skills.skill_config import SkillConfig

skill = SkillConfig(
    name=SkillName.ODOO_BUSINESS_ANALYST,
    system_prompt="Standard First — 90% problemów da się rozwiązać konfiguracją",
    allowed_tools=["odoo_search", "odoo_schema", "odoo_create", "search_knowledge_base", "scaffold_module", "read_odoo_log", "search_odoo_code"],
    red_flags=["no_code_generation"],
    recommended_model="claude-3-5-sonnet",
)
