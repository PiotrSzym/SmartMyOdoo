from typing import Dict
from smartmyodoo.swarm.models import SkillName
from smartmyodoo.swarm.skills.skill_config import SkillConfig

from .odoo_business_analyst import skill as odoo_business_analyst_skill
from .odoo_crud import skill as odoo_crud_skill
from .odoo_etl_manager import skill as odoo_etl_manager_skill
from .financial_audit import skill as financial_audit_skill
from .odoo_audit_history import skill as odoo_audit_history_skill
from .security_audit import skill as security_audit_skill

SKILL_REGISTRY: Dict[SkillName, SkillConfig] = {
    odoo_business_analyst_skill.name: odoo_business_analyst_skill,
    odoo_crud_skill.name: odoo_crud_skill,
    odoo_etl_manager_skill.name: odoo_etl_manager_skill,
    financial_audit_skill.name: financial_audit_skill,
    odoo_audit_history_skill.name: odoo_audit_history_skill,
    security_audit_skill.name: security_audit_skill,
}
