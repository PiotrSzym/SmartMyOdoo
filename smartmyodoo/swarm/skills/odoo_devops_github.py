from smartmyodoo.swarm.models import SkillName
from smartmyodoo.swarm.skills.skill_config import SkillConfig

skill = SkillConfig(
    name=SkillName.ODOO_DEVOPS_GITHUB,
    system_prompt="Staging Isolation, Feature Branches, version bump in __manifest__",
    allowed_tools=["rag"],
    red_flags=["no_force_push_production", "no_dns_change"],
    recommended_model="claude-3-5-sonnet"
)
