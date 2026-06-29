"""SH-LOG-01: domena `logs` — parser wklejanych logów Odoo.sh.

Endpoint `/api/logs/parse` zamienia surowy tekst logu na strukturę (wpisy + summary
z root cause bottom-up). Wymaga auth (Bearer) — log może zawierać dane wrażliwe
(zapytania SQL, e-maile, ścieżki), więc nie wystawiamy go publicznie.
"""

from typing import Tuple

from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException

from smartmyodoo.core.odoo_sh_log_parser import parse_odoo_sh_log
from smartmyodoo.api_deps import require_auth

router = APIRouter(tags=["logs"])

_MAX_CHARS = 2_000_000  # ~2 MB tekstu — bezpiecznik na olbrzymie wklejki.


class LogParseRequest(BaseModel):
    text: str = Field(..., description="Surowy tekst logów Odoo.sh do sparsowania")


@router.post("/api/logs/parse")
async def parse_logs(
    req: LogParseRequest,
    auth_data: Tuple[bytes, str, str] = Depends(require_auth),
):
    if len(req.text) > _MAX_CHARS:
        raise HTTPException(
            status_code=413,
            detail=f"Log za duży ({len(req.text)} znaków). Limit to {_MAX_CHARS}.",
        )
    return parse_odoo_sh_log(req.text).to_dict()
