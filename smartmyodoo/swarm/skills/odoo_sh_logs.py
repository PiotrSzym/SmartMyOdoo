from smartmyodoo.swarm.models import SkillName
from smartmyodoo.swarm.skills.skill_config import SkillConfig

skill = SkillConfig(
    name=SkillName.ODOO_SH_LOGS,
    system_prompt="Tracebacki bottom-up, rozróżniaj logi aplikacji vs deployment",
    allowed_tools=["rag"],
    red_flags=[],
    recommended_model="claude-3-5-sonnet",
)
