from smartmyodoo.swarm.skills.registry import SKILL_REGISTRY


def test_registry_size():
    assert len(SKILL_REGISTRY) == 12


def test_registry_valid_prompts():
    for name, skill in SKILL_REGISTRY.items():
        assert len(skill.system_prompt) > 0
        assert skill.name == name
