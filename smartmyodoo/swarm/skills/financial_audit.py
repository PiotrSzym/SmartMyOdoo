from smartmyodoo.swarm.models import SkillName
from smartmyodoo.swarm.skills.skill_config import SkillConfig

skill = SkillConfig(
    name=SkillName.FINANCIAL_AUDIT,
    system_prompt="Lock Dates Respect — Credit Note zamiast Cancel",
    allowed_tools=["xmlrpc_read"],
    red_flags=["no_write_to_posted_moves"],
    read_only=True,
    recommended_model="claude-3-5-sonnet"
)
