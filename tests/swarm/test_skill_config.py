import pytest
from pydantic import ValidationError
from smartmyodoo.swarm.models import SkillName
from smartmyodoo.swarm.skills.skill_config import SkillConfig


def test_skill_config_valid():
    config = SkillConfig(
        name=SkillName.ODOO_CRUD,
        system_prompt="You are a CRUD expert.",
        allowed_tools=["xmlrpc"],
        red_flags=["no_delete"],
        recommended_model="claude-3-5-sonnet",
    )
    assert config.name == SkillName.ODOO_CRUD
    assert config.system_prompt == "You are a CRUD expert."
    assert config.read_only is False
    assert config.requires_shadow_mode is False
    assert config.requires_human_override is False


def test_skill_config_missing_prompt():
    # Empty prompt should be rejected
    with pytest.raises(ValidationError):
        SkillConfig(
            name=SkillName.ODOO_CRUD,
            system_prompt="",
            allowed_tools=["xmlrpc"],
            red_flags=[],
            recommended_model="claude-3-5-sonnet",
        )
