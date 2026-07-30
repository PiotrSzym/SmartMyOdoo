from typing import Dict
from smartmyodoo.swarm.models import SkillName
from smartmyodoo.swarm.skills.skill_config import SkillConfig

from .odoo_business_analyst import skill as odoo_business_analyst_skill
from .odoo_crud import skill as odoo_crud_skill
from .odoo_etl_manager import skill as odoo_etl_manager_skill
from .financial_audit import skill as financial_audit_skill
from .odoo_audit_history import skill as odoo_audit_history_skill
from .security_audit import skill as security_audit_skill
from .odoo_developer import skill as odoo_developer_skill
from .odoo_devops_github import skill as odoo_devops_github_skill
from .odoo_sh_logs import skill as odoo_sh_logs_skill
from .odoo_api_expert import skill as odoo_api_expert_skill
from .magic_fix import skill as magic_fix_skill
from .odoo_mail_config import skill as odoo_mail_config_skill
from .odoo_website_embed import skill as odoo_website_embed_skill

SKILL_REGISTRY: Dict[SkillName, SkillConfig] = {
    odoo_business_analyst_skill.name: odoo_business_analyst_skill,
    odoo_crud_skill.name: odoo_crud_skill,
    odoo_etl_manager_skill.name: odoo_etl_manager_skill,
    financial_audit_skill.name: financial_audit_skill,
    odoo_audit_history_skill.name: odoo_audit_history_skill,
    security_audit_skill.name: security_audit_skill,
    odoo_developer_skill.name: odoo_developer_skill,
    odoo_devops_github_skill.name: odoo_devops_github_skill,
    odoo_sh_logs_skill.name: odoo_sh_logs_skill,
    odoo_api_expert_skill.name: odoo_api_expert_skill,
    magic_fix_skill.name: magic_fix_skill,
    odoo_mail_config_skill.name: odoo_mail_config_skill,
    odoo_website_embed_skill.name: odoo_website_embed_skill,
}
