import pytest
from token_governor import TokenGovernor


def test_initial_state():
    governor = TokenGovernor(max_budget_usd=2.0)
    assert governor.max_budget_usd == 2.0
    assert governor.current_spend == 0.0
    assert governor.total_tokens == 0


def test_add_usage():
    governor = TokenGovernor(max_budget_usd=1.0)
    governor.add_usage(1000, 0.5)  # $0.50
    assert governor.current_spend == 0.5
    assert governor.total_tokens == 1000


def test_budget_exceed():
    governor = TokenGovernor(max_budget_usd=1.0)
    with pytest.raises(PermissionError, match="TOKEN GOVERNOR ALERT"):
        governor.add_usage(3000, 0.5)  # $1.50


def test_boundary():
    governor = TokenGovernor(max_budget_usd=1.0)
    # Exactly 1.0 shouldn't raise
    governor.add_usage(2000, 0.5)  # $1.00
    assert governor.current_spend == 1.0


def test_get_status():
    governor = TokenGovernor(max_budget_usd=1.0)
    governor.add_usage(1000, 0.5)
    status = governor.get_status()
    assert status["spent_usd"] == 0.5
    assert status["max_budget_usd"] == 1.0
    assert status["total_tokens"] == 1000
    assert status["can_continue"] is True


def test_env_config(monkeypatch):
    monkeypatch.setenv("MAX_BUDGET_USD", "5.0")
    # Need to import after setting env var, or reload module, or just test the logic manually
    import token_governor
    import importlib

    importlib.reload(token_governor)
    assert token_governor.governor.max_budget_usd == 5.0
