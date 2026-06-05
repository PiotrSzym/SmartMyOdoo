from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class IntentCategory(str, Enum):
    A_CODE_GENERATION = "A"
    B_DATABASE_ADMIN = "B"
    C_TESTING_QA = "C"
    D_DOCUMENTATION = "D"
    E_RESEARCH = "E"
    F_ARCHITECTURE = "F"
    G_PROJECT_MANAGEMENT = "G"
    H_GENERAL_CHAT = "H"


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
    persona: Persona = Field(description="Persona przypisana do obsługi zadania")
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


class ChatResponse(BaseModel):
    reply: str
    action_type: str
    proposal_data: ChatProposalData | None = None
