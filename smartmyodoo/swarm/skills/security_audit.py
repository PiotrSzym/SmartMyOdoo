from smartmyodoo.swarm.models import SkillName
from smartmyodoo.swarm.skills.skill_config import SkillConfig

skill = SkillConfig(
    name=SkillName.SECURITY_AUDIT,
    system_prompt="Client-side Pseudonymization (PII)",
    allowed_tools=["pii_middleware", "xmlrpc_read"],
    red_flags=[],
    read_only=True,
    recommended_model="claude-3-5-sonnet"
)
