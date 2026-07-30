from enum import Enum
from typing import Any, Literal
from pydantic import BaseModel, Field


class EnvironmentInfo(BaseModel):
    odoo_version: str
    edition: Literal["community", "enterprise", "unknown"]
    hosting_type: Literal["saas", "odoo_sh", "on_premise", "unknown"]


class IntentCategory(str, Enum):
    A_CODE_GENERATION = "A"
    B_DATABASE_ADMIN = "B"
    C_TESTING_QA = "C"
    D_DOCUMENTATION = "D"
    E_RESEARCH = "E"
    F_ARCHITECTURE = "F"
    G_PROJECT_MANAGEMENT = "G"
    H_GENERAL_CHAT = "H"


class SkillName(str, Enum):
    ODOO_BUSINESS_ANALYST = "ODOO_BUSINESS_ANALYST"
    ODOO_DEVELOPER = "ODOO_DEVELOPER"
    ODOO_DEVOPS_GITHUB = "ODOO_DEVOPS_GITHUB"
    ODOO_SH_LOGS = "ODOO_SH_LOGS"
    ODOO_AUDIT_HISTORY = "ODOO_AUDIT_HISTORY"
    ODOO_CRUD = "ODOO_CRUD"
    ODOO_ETL_MANAGER = "ODOO_ETL_MANAGER"
    FINANCIAL_AUDIT = "FINANCIAL_AUDIT"
    SECURITY_AUDIT = "SECURITY_AUDIT"
    ODOO_API_EXPERT = "ODOO_API_EXPERT"
    MAGIC_FIX = "MAGIC_FIX"
    ODOO_MAIL_CONFIG = "ODOO_MAIL_CONFIG"
    ODOO_WEBSITE_EMBED = "ODOO_WEBSITE_EMBED"


class Persona(str, Enum):
    DEV = "Developer"
    DBA = "Database Administrator"
    QA = "Quality Assurance"
    DOCS = "Technical Writer"
    SCOUT = "Scout / Researcher"
    ARCH = "Architect"
    PM = "Project Manager"
    GENERIC = "Generic Assistant"


class DispatchResult(BaseModel):
    category: IntentCategory = Field(
        description="Zidentyfikowana kategoria intencji (A-H)"
    )
    persona: Persona | None = Field(
        default=None, description="Persona przypisana do obsługi zadania"
    )
    skill_name: SkillName | None = Field(
        default=None, description="Konkretny skill z registry przypisany do zadania"
    )
    recommended_model: str = Field(
        description="Zalecany model LLM do realizacji zadania"
    )
    confidence: float = Field(default=1.0, description="Pewność routera (0.0 - 1.0)")


class ChatProposalData(BaseModel):
    proposal_id: str
    text: str
    model: str
    method: str
    args: list[Any]


class ChatRequest(BaseModel):
    message: str
    user_id: int
    active_model: str | None = None
    active_id: int | None = None
    session_id: str
    workspace_id: str = "default"
    selected_skills: list[str] | None = None
    # WRITE-02 T1: stan kłódki UI (🟢 read / 🔴 edit). Backend NIE ufa modelowi —
    # w trybie read write-tool jest deterministycznie blokowany (autoryzacja = przełączenie 🔴+PIN).
    edit_mode: bool = False


class ChatResponse(BaseModel):
    reply: str
    action_type: str
    proposal_data: ChatProposalData | None = None
    category: str | None = None
    persona: str | None = None
    model: str | None = None
    selected_skills: list[str] | None = None


class Proposal(BaseModel):
    id: str
    workspace_id: str
    odoo_model: str
    method: str
    values: dict[str, Any] = {}
    reason: str = ""
    status: str = "pending"  # pending | approved | rejected
    created_at: str = ""


class WorkspaceInfo(BaseModel):
    id: str
    name: str
    odoo_url: str = ""
