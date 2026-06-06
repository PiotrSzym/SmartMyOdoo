from smartmyodoo.swarm.dispatcher import Dispatcher
from smartmyodoo.swarm.models import SkillName


def test_dispatcher_etl_manager():
    dispatcher = Dispatcher()
    result = dispatcher.classify_intent("Zaimportuj 5000 produktów do bazy")
    assert result.skill_name == SkillName.ODOO_ETL_MANAGER


def test_dispatcher_audit_history():
    dispatcher = Dispatcher()
    result = dispatcher.classify_intent("Sprawdź kto zmienił fakturę i kiedy")
    assert result.skill_name == SkillName.ODOO_AUDIT_HISTORY


def test_dispatcher_security():
    dispatcher = Dispatcher()
    result = dispatcher.classify_intent(
        "Zrób audyt PII i security dla modelu res.partner"
    )
    assert result.skill_name == SkillName.SECURITY_AUDIT
