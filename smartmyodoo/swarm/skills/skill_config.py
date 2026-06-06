from typing import List
from pydantic import BaseModel, Field
from smartmyodoo.swarm.models import SkillName


class SkillConfig(BaseModel):
    name: SkillName
    system_prompt: str = Field(min_length=1)
    allowed_tools: List[str]
    red_flags: List[str]
    read_only: bool = False
    requires_shadow_mode: bool = False
    requires_human_override: bool = False
    recommended_model: str
