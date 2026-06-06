from pydantic import BaseModel, Field
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


class SuccessResponse(BaseModel):
    success: bool
    message: Optional[str] = None


class ErrorResponse(BaseModel):
    error: str
