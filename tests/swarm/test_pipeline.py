import pytest
from unittest.mock import Mock
from smartmyodoo.swarm.pipeline import ExecutionPipeline, PipelineState
from smartmyodoo.swarm.db_manager import OdooDBManager
from smartmyodoo.swarm.adp import DecisionEngine
from smartmyodoo.swarm.recon import EnvironmentRecon
from smartmyodoo.swarm.models import EnvironmentInfo

from smartmyodoo.swarm.vault_auth import PipelineCredentials


@pytest.fixture
def mock_vault_auth(monkeypatch):
    creds = PipelineCredentials(
        odoo_url="http://test",
        odoo_db="test_db",
        odoo_login="admin",
        odoo_password="pwd",
        openrouter_key="sk-or",
    )
    mock_auth = Mock(return_value=creds)
    monkeypatch.setattr(
        "smartmyodoo.swarm.vault_auth.VaultAuthProvider.authenticate", mock_auth
    )
    return mock_auth


@pytest.fixture
def mock_db_manager():
    manager = Mock(spec=OdooDBManager)
    manager.duplicate_database.return_value = True
    manager.drop_database.return_value = True
    return manager


@pytest.fixture
def mock_decision_engine():
    engine = Mock(spec=DecisionEngine)
    engine.evaluate.return_value = {"8_Plan": "Test Plan"}
    return engine


@pytest.fixture
def mock_recon():
    recon = Mock(spec=EnvironmentRecon)
    recon.detect_version.return_value = EnvironmentInfo(
        odoo_version="18.0", edition="enterprise", hosting_type="odoo_sh"
    )
    return recon


def test_pipeline_happy_path(
    mock_db_manager, mock_decision_engine, mock_recon, mock_vault_auth
):
    pipeline = ExecutionPipeline(
        db_manager=mock_db_manager,
        decision_engine=mock_decision_engine,
        recon_engine=mock_recon,
    )

    pipeline.run("napisz modul", "Developer", "prod_db")

    # Sprawdzenie czy przeszedl przez wszystkie stany
    assert pipeline.state == PipelineState.SYNC

    # Sprawdzenie czy DB Manager zduplikowal baze
    mock_db_manager.duplicate_database.assert_called_once_with(
        "prod_db", "prod_db_agent_scratchpad"
    )

    # Sprawdzenie czy recon zostal uzyty
    mock_recon.detect_version.assert_called_once()
    assert pipeline.env_info.odoo_version == "18.0"

    # Sprawdzenie czy ADP zostal wywolany z env_info
    mock_decision_engine.evaluate.assert_called_once_with(
        "Developer", "napisz modul", pipeline.env_info
    )


def test_pipeline_rollback_on_recon_failure(
    mock_db_manager, mock_decision_engine, mock_recon, mock_vault_auth
):
    # Symulacja bledu Odoo DB (nie mozna sklonowac)
    mock_db_manager.duplicate_database.return_value = False

    pipeline = ExecutionPipeline(
        db_manager=mock_db_manager,
        decision_engine=mock_decision_engine,
        recon_engine=mock_recon,
    )

    pipeline.run("napisz modul", "Developer", "prod_db")

    # Klonowanie zawiodlo, wiec wywolal sie _execute_recon i rzucil wyjatek PipelineError.
    # W wyjatku wykonano rollback(), wiec stan koncowy to SYNC.
    assert pipeline.state == PipelineState.SYNC

    # Upewniamy sie, ze drop_database tez zostal wywolany by usunac niesprawny scratchpad
    mock_db_manager.drop_database.assert_called_once_with("prod_db_agent_scratchpad")


def test_pipeline_rollback_on_actuation_error(
    mock_db_manager, mock_decision_engine, mock_recon, mock_vault_auth
):
    pipeline = ExecutionPipeline(
        db_manager=mock_db_manager,
        decision_engine=mock_decision_engine,
        recon_engine=mock_recon,
    )

    # Nadpisujemy _execute_actuation aby wyrzucal blad
    pipeline._execute_actuation = Mock(
        side_effect=Exception("Brak prądu w serwerowni!")
    )

    pipeline.run("zrob cos zlego", "Developer", "prod_db")

    # Stan koncowy to SYNC
    assert pipeline.state == PipelineState.SYNC

    # Baza musiala byc usunieta bo doszlo do ACTUATION i wystapil blad
    mock_db_manager.drop_database.assert_called_once_with("prod_db_agent_scratchpad")


def test_adp_system_prompt():
    engine = DecisionEngine()
    env_info = EnvironmentInfo(
        odoo_version="18.0", edition="enterprise", hosting_type="odoo_sh"
    )
    result = engine.evaluate("Developer", "Stworz model", env_info)

    # Fallback/Mock dziala i zwraca wlasciwy slownik
    assert result["3_Wersja"] == "Odoo 18.0"
    assert result["6_Trudnosc"] == 3


# --- ARCH-01: Nowe testy integracyjne FSM ---


def test_pipeline_auth_failure_triggers_rollback(
    mock_db_manager, mock_decision_engine, mock_recon, monkeypatch
):
    """AUTH fail (VaultDecryptionError) → rollback, _rolled_back=True, state=SYNC."""
    from smartmyodoo.swarm.vault_auth import VaultAuthProvider

    def auth_boom(pin):
        raise Exception("VaultDecryptionError: Invalid PIN")

    monkeypatch.setattr(VaultAuthProvider, "authenticate", staticmethod(auth_boom))

    pipeline = ExecutionPipeline(
        db_manager=mock_db_manager,
        decision_engine=mock_decision_engine,
        recon_engine=mock_recon,
    )

    pipeline.run("test intent", "Developer", "prod_db")

    assert pipeline.state == PipelineState.SYNC
    assert pipeline._rolled_back is True
    # RECON never reached → no duplicate_database call
    mock_db_manager.duplicate_database.assert_not_called()


def test_pipeline_recon_failure_sets_rolled_back_flag(
    mock_db_manager, mock_decision_engine, mock_recon, mock_vault_auth
):
    """RECON fail (duplicate_database=False) → _rolled_back flag set to True."""
    mock_db_manager.duplicate_database.return_value = False

    pipeline = ExecutionPipeline(
        db_manager=mock_db_manager,
        decision_engine=mock_decision_engine,
        recon_engine=mock_recon,
    )

    pipeline.run("test intent", "Developer", "prod_db")

    assert pipeline.state == PipelineState.SYNC
    assert pipeline._rolled_back is True
    mock_db_manager.drop_database.assert_called_once_with("prod_db_agent_scratchpad")


def test_pipeline_cognitive_tool_restriction():
    """COGNITIVE phase returns empty tool list (intentional — planning only)."""
    pipeline = ExecutionPipeline(
        db_manager=Mock(spec=OdooDBManager),
        decision_engine=Mock(spec=DecisionEngine),
    )

    allowed = pipeline.get_allowed_tools_for_phase(PipelineState.COGNITIVE)
    assert allowed == []

    # Also verify AUTH and SYNC return empty
    assert pipeline.get_allowed_tools_for_phase(PipelineState.AUTH) == []
    assert pipeline.get_allowed_tools_for_phase(PipelineState.SYNC) == []


def test_pipeline_recon_tool_restriction():
    """RECON phase returns only read-only tools, never write tools."""
    pipeline = ExecutionPipeline(
        db_manager=Mock(spec=OdooDBManager),
        decision_engine=Mock(spec=DecisionEngine),
    )

    allowed = pipeline.get_allowed_tools_for_phase(PipelineState.RECON)

    # Must contain read-only tools
    assert "odoo_search" in allowed
    assert "odoo_schema" in allowed
    assert "search_knowledge_base" in allowed

    # Must NOT contain write tools
    assert "odoo_create" not in allowed
    assert "odoo_write" not in allowed
    assert "odoo_unlink" not in allowed


def test_pipeline_transition_callback_called(
    mock_db_manager, mock_decision_engine, mock_recon, mock_vault_auth
):
    """on_transition_callback is invoked for every FSM state transition."""
    callback = Mock()

    pipeline = ExecutionPipeline(
        db_manager=mock_db_manager,
        decision_engine=mock_decision_engine,
        recon_engine=mock_recon,
        on_transition_callback=callback,
    )

    pipeline.run("test intent", "Developer", "prod_db")

    # Happy path: AUTH → RECON → COGNITIVE → ACTUATION → SYNC = 5 transitions
    assert callback.call_count == 5
    call_args = [c.args[0] for c in callback.call_args_list]
    assert call_args == ["AUTH", "RECON", "COGNITIVE", "ACTUATION", "SYNC"]
