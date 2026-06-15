"""S2.6 (dowód): pipeline dobiera skill z routingu (Dispatcher), nie hardkoduje ODOO_DEVELOPER.

PRZED naprawą: COGNITIVE i ACTUATION zawsze budowały SkillConfig(name=ODOO_DEVELOPER),
a ROUTING_TABLE/classify_intent były martwe dla pipeline.
PO naprawie: pipeline._resolve_skill klasyfikuje intencję i przekazuje właściwy skill+red_flags.
"""

from unittest.mock import MagicMock

from smartmyodoo.swarm.dispatcher import Dispatcher
from smartmyodoo.swarm.models import SkillName
from smartmyodoo.swarm.pipeline import ExecutionPipeline, PipelineState


class SpyExecutor:
    sandbox = None

    def __init__(self):
        self.configs = []

    def execute(self, config, message, phase_restrictions=None):
        self.configs.append(config)
        return {"response": "ok"}


def test_resolve_skill_from_routing():
    pipe = ExecutionPipeline(
        db_manager=MagicMock(), decision_engine=MagicMock(), dispatcher=Dispatcher()
    )
    skill, model, red_flags = pipe._resolve_skill("zrób migrację bazy danych")

    assert skill == SkillName.ODOO_CRUD  # NIE hardkodowany ODOO_DEVELOPER
    assert "no_delete_posted_invoice" in red_flags  # red_flags z routowanego skilla


def test_cognitive_uses_routed_skill_not_hardcoded():
    spy = SpyExecutor()
    pipe = ExecutionPipeline(
        db_manager=MagicMock(),
        decision_engine=MagicMock(),
        executor=spy,
        dispatcher=Dispatcher(),
    )
    pipe._skill_name, pipe._model, pipe._red_flags = pipe._resolve_skill(
        "import 5000 produktów"
    )
    pipe.state = PipelineState.COGNITIVE
    pipe.env_info = None

    pipe._execute_cognitive("import 5000 produktów", "DBA")

    assert spy.configs, "executor.execute nie został wywołany"
    assert (
        spy.configs[0].name == SkillName.ODOO_ETL_MANAGER
    )  # routing → ETL, nie DEVELOPER


def test_no_dispatcher_falls_back_to_developer():
    pipe = ExecutionPipeline(db_manager=MagicMock(), decision_engine=MagicMock())
    skill, _model, _red = pipe._resolve_skill("cokolwiek bez routera")
    assert skill == SkillName.ODOO_DEVELOPER
