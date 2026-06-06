from smartmyodoo.swarm.models import SkillName
from smartmyodoo.swarm.skills.skill_config import SkillConfig

skill = SkillConfig(
    name=SkillName.ODOO_API_EXPERT,
    system_prompt="API Keys zamiast hasła admina, nigdy auth='public' dla partnerów",
    allowed_tools=["xmlrpc", "rag"],
    red_flags=["no_auth_public_partners", "no_plaintext_password"],
    recommended_model="claude-3-5-sonnet"
)
