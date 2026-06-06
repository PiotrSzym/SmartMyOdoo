from smartmyodoo.swarm.models import SkillName
from smartmyodoo.swarm.skills.skill_config import SkillConfig

skill = SkillConfig(
    name=SkillName.ODOO_AUDIT_HISTORY,
    system_prompt="Chatter tracking via mail.message",
    allowed_tools=["xmlrpc_read"],
    red_flags=[],
    read_only=True,
    recommended_model="claude-3-5-sonnet"
)
