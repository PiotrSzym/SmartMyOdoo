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
    # K6 (KEY-01): typowany rejestr — typ klucza + provider LLM + domyślne ref timesheet
    type: Optional[str] = ""  # odoo_data | odoo_timesheet | llm_provider | git_token | api_token | ssh_key
    provider: Optional[str] = ""  # openrouter | anthropic | openai (tylko llm_provider)
    default_project_ref: Optional[str] = ""  # tylko odoo_timesheet
    default_task_ref: Optional[str] = ""  # tylko odoo_timesheet
    # VCS / API token
    host: Optional[str] = ""  # np. 'github.com' (git_token/api_token)
    scopes: Optional[str] = ""  # opis uprawnień (audyt/rotacja)
    resource_owner: Optional[str] = ""  # org dla fine-grained (git_token)


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
    GIT_TOKEN = "git_token"  # token VCS (GitHub/GitLab) — dla git/gh (api_key=token, host=serwer)
    SSH_KEY = "ssh_key"  # klucz SSH (np. odoo.sh deploy) — key/pubkey/key_path
    API_TOKEN = "api_token"  # generyczny token API (Fireflies itp.) — api_key wymagany


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
    # VCS / API token (KEY-03: git_token/api_token)
    host: Optional[str] = None  # np. 'github.com' — serwer VCS/API
    scopes: Optional[str] = None  # opis uprawnień tokenu (do audytu/rotacji)
    resource_owner: Optional[str] = None  # org dla tokenu fine-grained (np. 'myOdoo-pl')
    # SSH (KEY-03: ssh_key — formalizacja istniejącego ODOO_SH_SSH)
    key: Optional[str] = None  # prywatny klucz (PEM) — trzymany zaszyfrowany w vault
    pubkey: Optional[str] = None  # klucz publiczny (jawny)
    key_path: Optional[str] = None  # ścieżka do pliku klucza na dysku (alternatywa dla key)

    @model_validator(mode="after")
    def _validate_by_type(self) -> "Credential":
        if self.type == CredentialType.LLM_PROVIDER:
            if not self.provider or not self.api_key:
                raise ValueError("llm_provider wymaga pól: provider, api_key")
        elif self.type in (CredentialType.ODOO_DATA, CredentialType.ODOO_TIMESHEET):
            missing = [f for f in ("url", "db", "login") if not getattr(self, f)]
            if missing:
                raise ValueError(f"{self.type.value} wymaga pól: {', '.join(missing)}")
        elif self.type == CredentialType.GIT_TOKEN:
            missing = [f for f in ("api_key", "host") if not getattr(self, f)]
            if missing:
                raise ValueError(f"git_token wymaga pól: {', '.join(missing)}")
        elif self.type == CredentialType.API_TOKEN:
            if not self.api_key:
                raise ValueError("api_token wymaga pola: api_key")
        elif self.type == CredentialType.SSH_KEY:
            if not (self.key or self.key_path):
                raise ValueError("ssh_key wymaga pola: key lub key_path")
        return self


class SuccessResponse(BaseModel):
    success: bool
    message: Optional[str] = None


class ErrorResponse(BaseModel):
    error: str
