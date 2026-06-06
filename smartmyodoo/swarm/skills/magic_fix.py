from smartmyodoo.swarm.models import SkillName
from smartmyodoo.swarm.skills.skill_config import SkillConfig

skill = SkillConfig(
    name=SkillName.MAGIC_FIX,
    system_prompt="Force unlock, omijanie ORM tylko w sytuacji kryzysowej",
    allowed_tools=["database_magic", "shadow_mode"],
    red_flags=["no_drop_table", "no_truncate"],
    requires_human_override=True,
    requires_shadow_mode=True,
    recommended_model="claude-3-5-sonnet"
)
