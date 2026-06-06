from smartmyodoo.swarm.models import SkillName
from smartmyodoo.swarm.skills.skill_config import SkillConfig

skill = SkillConfig(
    name=SkillName.SECURITY_AUDIT,
    system_prompt="Client-side Pseudonymization (PII)",
    allowed_tools=["odoo_search", "odoo_schema", "odoo_create", "search_knowledge_base", "scaffold_module", "read_odoo_log", "search_odoo_code"],
    red_flags=[],
    read_only=True,
    recommended_model="claude-3-5-sonnet",
)
