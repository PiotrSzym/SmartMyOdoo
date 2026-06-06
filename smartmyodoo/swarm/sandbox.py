"""
Sandbox Manager — automatyczne tworzenie Scratchpad DB przy write tools.

Przy KAŻDYM wywołaniu narzędzia modyfikującego (odoo_create, odoo_update, odoo_delete)
system automatycznie klonuje bazę Odoo, wykonuje operację na klonie,
a w razie błędu — cofa zmiany (rollback = drop klona).
"""

import logging
import os
from typing import Optional

from smartmyodoo.swarm.db_manager import OdooDBManager

logger = logging.getLogger(__name__)

# Narzędzia które WYMAGAJĄ sandboxa
WRITE_TOOLS = frozenset({"odoo_create", "odoo_update", "odoo_delete"})


class SandboxManager:
    """
    Zarządzanie Scratchpad DB dla bezpiecznego wykonywania operacji write.
    """

    def __init__(
        self,
        odoo_url: Optional[str] = None,
        master_password: Optional[str] = None,
    ):
        self.odoo_url = odoo_url or os.environ.get("ODOO_URL", "http://localhost:8069")
        self.master_password = master_password or os.environ.get("ODOO_MASTER_PASSWORD", "admin")
        self.db_manager = OdooDBManager(self.odoo_url, self.master_password)
        self._active_scratchpad: Optional[str] = None
        self._original_db: Optional[str] = None
        self.enabled = os.environ.get("SANDBOX_ENABLED", "true").lower() == "true"

    def is_write_tool(self, tool_name: str) -> bool:
        """Sprawdza czy narzędzie wymaga sandboxa."""
        return tool_name in WRITE_TOOLS

    def enter_sandbox(self, original_db: str) -> Optional[str]:
        """
        Tworzy Scratchpad DB (klon oryginalnej bazy).
        Zwraca nazwę scratchpad DB lub None jeśli sandbox wyłączony / błąd.
        """
        if not self.enabled:
            logger.info("Sandbox wyłączony (SANDBOX_ENABLED=false)")
            return None

        if self._active_scratchpad:
            logger.info(f"Scratchpad już aktywny: {self._active_scratchpad}")
            return self._active_scratchpad

        self._original_db = original_db
        scratchpad_name = f"{original_db}_agent_scratchpad"

        logger.info(f"🔒 Tworzenie Scratchpad DB: {scratchpad_name}")
        success = self.db_manager.duplicate_database(original_db, scratchpad_name)

        if success:
            self._active_scratchpad = scratchpad_name
            return scratchpad_name
        else:
            logger.error("Nie udało się utworzyć Scratchpad DB — operacja write bez sandboxa!")
            return None

    def exit_sandbox(self, success: bool = True) -> None:
        """
        Zamyka sandbox.
        - success=True: loguje sukces, Scratchpad zostaje do audytu
        - success=False: ROLLBACK — usuwa Scratchpad DB
        """
        if not self._active_scratchpad:
            return

        if success:
            logger.info(
                f"✅ Sandbox zakończony sukcesem. "
                f"Scratchpad '{self._active_scratchpad}' zachowany do audytu."
            )
        else:
            logger.warning(
                f"⚠️ ROLLBACK: Usuwanie Scratchpad DB '{self._active_scratchpad}'"
            )
            self.db_manager.drop_database(self._active_scratchpad)

        self._active_scratchpad = None
        self._original_db = None

    @property
    def active_scratchpad(self) -> Optional[str]:
        return self._active_scratchpad
