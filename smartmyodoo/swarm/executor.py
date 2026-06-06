import re
from typing import Dict, Any, Optional

from smartmyodoo.swarm.skills.skill_config import SkillConfig

class RedFlagViolation(Exception):
    """Raised when a user intent matches a configured red flag for a skill."""
    pass

class SkillExecutor:
    def __init__(self, llm_client: Optional[Any] = None):
        self.llm_client = llm_client

    def execute(self, skill_config: SkillConfig, message: str) -> Dict[str, Any]:
        """
        Executes a given message against the skill configuration.
        """
        # 1. Red Flag Detection
        for flag in skill_config.red_flags:
            if re.search(flag, message, re.IGNORECASE):
                raise RedFlagViolation(f"Red flag triggered: {flag}")

        # 2. Filter Tools
        tools = list(skill_config.allowed_tools)
        if skill_config.read_only and "shadow_mode" in tools:
            tools.remove("shadow_mode")

        # 3. Call LLM
        response_text = ""
        if self.llm_client:
            # Here you would typically build the prompt including system_prompt
            # prompt = f"{skill_config.system_prompt}\n\nUser: {message}"
            response_text = self.llm_client.generate(message)

        # 4. Return result
        return {
            "response": response_text,
            "requires_human_override": skill_config.requires_human_override,
            "tools_used": tools,
        }
