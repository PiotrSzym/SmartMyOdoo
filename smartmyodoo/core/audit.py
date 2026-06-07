"""
Audit Trail — zapis każdego wywołania narzędzia do tabeli AuditLog.

Zgodność: SOC2 / GDPR Art.30 — każda mutacja danych musi mieć wpis.
Sanityzacja: nie loguje haseł, kluczy API (wzorzec Deny List).
"""

import json
import logging
import re
from typing import Any, Optional

from sqlalchemy.orm import Session

from smartmyodoo.core.models import AuditLog

logger = logging.getLogger(__name__)

# Deny List — pola które NIE powinny trafić do audit log
_SENSITIVE_PATTERNS = re.compile(
    r"(password|passwd|secret|api_key|apikey|token|pin|master_pwd|credentials)",
    re.IGNORECASE,
)


def _sanitize_details(data: Any) -> str:
    """Usuwa wrażliwe dane z detali audytu."""
    if isinstance(data, dict):
        sanitized = {}
        for k, v in data.items():
            if _SENSITIVE_PATTERNS.search(k):
                sanitized[k] = "***REDACTED***"
            else:
                sanitized[k] = _sanitize_details(v)
        return json.dumps(sanitized, ensure_ascii=False, default=str)
    if isinstance(data, str):
        # Truncate very long strings
        if len(data) > 500:
            return data[:500] + "...[TRUNCATED]"
        return data
    return json.dumps(data, ensure_ascii=False, default=str)


def log_tool_call(
    db: Session,
    workspace_id: str,
    tool_name: str,
    args: dict,
    result: str,
    success: bool = True,
) -> None:
    """Loguje wywołanie narzędzia do tabeli AuditLog."""
    status = "OK" if success else "ERROR"
    details = _sanitize_details(
        {
            "tool": tool_name,
            "args": args,
            "result_preview": str(result)[:200],
            "status": status,
        }
    )

    entry = AuditLog(
        workspace_id=workspace_id,
        action=f"TOOL:{tool_name}:{status}",
        details=details,
    )
    try:
        db.add(entry)
        db.commit()
    except Exception as e:
        logger.warning(f"Audit log write failed: {e}")
        db.rollback()


def log_event(
    db: Session,
    workspace_id: str,
    action: str,
    details: Optional[str] = None,
) -> None:
    """Loguje ogólne zdarzenie (np. login, session start)."""
    entry = AuditLog(
        workspace_id=workspace_id,
        action=action,
        details=details or "",
    )
    try:
        db.add(entry)
        db.commit()
    except Exception as e:
        logger.warning(f"Audit log write failed: {e}")
        db.rollback()
