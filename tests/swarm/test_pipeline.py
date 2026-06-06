import pytest
from unittest.mock import Mock
from smartmyodoo.swarm.pipeline import ExecutionPipeline, PipelineState
from smartmyodoo.swarm.db_manager import OdooDBManager
from smartmyodoo.swarm.adp import DecisionEngine
from smartmyodoo.swarm.recon import EnvironmentRecon
from smartmyodoo.swarm.models import EnvironmentInfo


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
        odoo_version="18.0",
        edition="enterprise",
        hosting_type="odoo_sh"
    )
    return recon


def test_pipeline_happy_path(mock_db_manager, mock_decision_engine, mock_recon):
    pipeline = ExecutionPipeline(
        db_manager=mock_db_manager, 
        decision_engine=mock_decision_engine,
        recon_engine=mock_recon
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
        "Developer", 
        "napisz modul",
        pipeline.env_info
    )


def test_pipeline_rollback_on_recon_failure(mock_db_manager, mock_decision_engine, mock_recon):
    # Symulacja bledu Odoo DB (nie mozna sklonowac)
    mock_db_manager.duplicate_database.return_value = False

    pipeline = ExecutionPipeline(
        db_manager=mock_db_manager, 
        decision_engine=mock_decision_engine,
        recon_engine=mock_recon
    )

    pipeline.run("napisz modul", "Developer", "prod_db")

    # Klonowanie zawiodlo, wiec wywolal sie _execute_recon i rzucil wyjatek PipelineError.
    # W wyjatku wykonano rollback(), wiec stan koncowy to SYNC.
    assert pipeline.state == PipelineState.SYNC

    # Upewniamy sie, ze drop_database tez zostal wywolany by usunac niesprawny scratchpad
    mock_db_manager.drop_database.assert_called_once_with("prod_db_agent_scratchpad")


def test_pipeline_rollback_on_actuation_error(mock_db_manager, mock_decision_engine, mock_recon):
    pipeline = ExecutionPipeline(
        db_manager=mock_db_manager, 
        decision_engine=mock_decision_engine,
        recon_engine=mock_recon
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
        odoo_version="18.0",
        edition="enterprise",
        hosting_type="odoo_sh"
    )
    result = engine.evaluate("Developer", "Stworz model", env_info)

    # Fallback/Mock dziala i zwraca wlasciwy slownik
    assert result["3_Wersja"] == "Odoo 18.0"
    assert result["6_Trudnosc"] == 3
