from sqlalchemy import Column, Integer, String, Text, DateTime, Float
from sqlalchemy.sql import func
from .database import Base


class Workspace(Base):
    __tablename__ = "workspaces"
    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    odoo_url = Column(String, default="")
    position = Column(Integer, default=0)
    task_ref = Column(String, default="")  # Odoo project.task ID
    task_name = Column(String, default="")  # Cached display name
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ChatMessage(Base):
    """Persystentna historia chatu — każda wiadomość user/assistant/tool."""
    __tablename__ = "chat_messages"
    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(String, default="default", index=True)
    session_id = Column(String, index=True)
    role = Column(String)  # "user" | "assistant" | "tool"
    content = Column(Text)
    metadata_json = Column(Text, default="{}")  # persona, category, tools_used
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class AuditLog(Base):
    __tablename__ = "audit_log"
    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(String, default="default", index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    action = Column(String)
    details = Column(Text)


class TokenUsage(Base):
    __tablename__ = "token_usage"
    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(String, default="default", index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    model = Column(String)
    tokens_used = Column(Integer)
    cost = Column(Float)


class Proposal(Base):
    __tablename__ = "proposals"
    id = Column(String, primary_key=True, index=True)
    workspace_id = Column(String, default="default", index=True)
    odoo_model = Column(String, default="")
    method = Column(String, default="")
    values = Column(String, default="{}")
    reason = Column(String, default="")
    status = Column(String, default="pending")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
