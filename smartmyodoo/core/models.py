from sqlalchemy import Column, Integer, String, Text, DateTime, Float
from sqlalchemy.sql import func
from .database import Base

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
    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(String, default="default", index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    status = Column(String)
    plan_json = Column(Text)


