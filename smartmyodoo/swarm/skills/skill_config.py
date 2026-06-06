from typing import List
from pydantic import BaseModel, Field, model_validator
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

    @model_validator(mode='after')
    def validate_tools(self) -> 'SkillConfig':
        from smartmyodoo.swarm.tools import TOOL_REGISTRY
        for tool in self.allowed_tools:
            if tool not in TOOL_REGISTRY:
                raise ValueError(f"Tool '{tool}' is not registered in TOOL_REGISTRY.")
        return self
