from enum import Enum
from pydantic import BaseModel, Field, model_validator
from typing import Optional


class InitRequest(BaseModel):
    pin: str = Field(..., min_length=4, description="PIN do lokalnego odszyfrowywania")
    master: str = Field(..., min_length=8, description="Master Password do zarządzania")


class AuthRequest(BaseModel):
    password: str = Field(..., description="PIN lub Master Password")


class AuthResponse(BaseModel):
    success: bool
    role: Optional[str] = None
    error: Optional[str] = None


class WorkspaceCreateRequest(BaseModel):
    id: str
    name: str
    odoo_url: Optional[str] = ""
    admin_login: Optional[str] = None
    admin_password: Optional[str] = None
    admin_api_key: Optional[str] = None
    admin_expires: Optional[str] = None


class SecretCreateRequest(BaseModel):
    password: str
    login: Optional[str] = ""
    url: Optional[str] = ""
    db: Optional[str] = ""
    api_key: Optional[str] = ""
    expires: Optional[str] = ""
    workspace_id: Optional[str] = "default"


class SecretResponse(BaseModel):
    password: str
    login: str
    url: str
    db: Optional[str] = ""
    api_key: str
    expires: str
    workspace_id: Optional[str] = "default"
    deleted_at: Optional[str] = None


class ChangePinRequest(BaseModel):
    new_pin: str = Field(..., min_length=4)


class CredentialType(str, Enum):
    """K1 (KEY-01): typ poświadczenia — decyduje DO CZEGO służy (nie nazwa sekretu)."""

    ODOO_DATA = "odoo_data"  # Odoo klienta — czytanie/zapis danych
    ODOO_TIMESHEET = "odoo_timesheet"  # Odoo do logowania czasu pracy (może być inne)
    LLM_PROVIDER = "llm_provider"  # klucz do modeli AI


class Credential(BaseModel):
    """Typowane poświadczenie. System rozpoznaje je po `type`+`workspace`(+`provider`),
    a nie po magicznej nazwie. `name` to tylko etykieta dla człowieka.
    """

    name: str = Field(..., min_length=1, description="Etykieta dla człowieka")
    type: CredentialType
    workspace_id: str = "default"
    enabled: bool = True
    # LLM
    provider: Optional[str] = None  # np. 'openrouter' | 'anthropic' | 'openai'
    api_key: Optional[str] = None
    # Odoo (data/timesheet)
    url: Optional[str] = None
    db: Optional[str] = None
    login: Optional[str] = None
    password: Optional[str] = None
    # binding (timesheet)
    default_project_ref: Optional[str] = None
    default_task_ref: Optional[str] = None

    @model_validator(mode="after")
    def _validate_by_type(self) -> "Credential":
        if self.type == CredentialType.LLM_PROVIDER:
            if not self.provider or not self.api_key:
                raise ValueError("llm_provider wymaga pól: provider, api_key")
        elif self.type in (CredentialType.ODOO_DATA, CredentialType.ODOO_TIMESHEET):
            missing = [f for f in ("url", "db", "login") if not getattr(self, f)]
            if missing:
                raise ValueError(f"{self.type.value} wymaga pól: {', '.join(missing)}")
        return self


class SuccessResponse(BaseModel):
    success: bool
    message: Optional[str] = None


class ErrorResponse(BaseModel):
    error: str
