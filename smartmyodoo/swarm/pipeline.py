from enum import Enum, auto
import logging
from typing import Dict, Any, Optional
from .adp import DecisionEngine
from .db_manager import OdooDBManager
from .recon import EnvironmentRecon
from .models import EnvironmentInfo

logger = logging.getLogger(__name__)


class PipelineState(Enum):
    AUTH = auto()
    RECON = auto()
    COGNITIVE = auto()
    ACTUATION = auto()
    SYNC = auto()


class PipelineError(Exception):
    """Błąd przerywający działanie Pipeline-u"""

    pass


class ExecutionPipeline:
    """
    Maszyna Stanów (FSM) sterująca działaniem Agenta od autoryzacji do aktuacji,
    zawierająca mechanizm Scratchpad DB i rollback.
    """

    def __init__(self, db_manager: OdooDBManager, decision_engine: DecisionEngine, recon_engine: Optional[EnvironmentRecon] = None):
        self.state = PipelineState.AUTH
        self.db_manager = db_manager
        self.decision_engine = decision_engine
        self.recon_engine = recon_engine

        # Kontekst wykonania
        self.original_db: str = ""
        self.scratchpad_db: str = ""
        self.adp_plan: Dict[str, Any] = {}
        self.env_info: Optional[EnvironmentInfo] = None

    def run(self, intent: str, persona: str, original_db: str):
        """Uruchamia pełen cykl FSM dla danego zadania."""
        self.original_db = original_db
        self.scratchpad_db = f"{original_db}_agent_scratchpad"

        try:
            self._transition_to(PipelineState.AUTH)
            self._execute_auth()

            self._transition_to(PipelineState.RECON)
            self._execute_recon()

            self._transition_to(PipelineState.COGNITIVE)
            self._execute_cognitive(intent, persona)

            self._transition_to(PipelineState.ACTUATION)
            self._execute_actuation()

            self._transition_to(PipelineState.SYNC)
            self._execute_sync(success=True)

        except Exception as e:
            logger.error(f"Pipeline przerwany z błędem: {str(e)}")
            self.rollback()

    def rollback(self):
        """Wycofuje stan z powrotem do SYNC, usuwając środowisko robocze."""
        logger.warning(f"Inicjacja procedury Rollback dla bazy {self.scratchpad_db}")
        if self.scratchpad_db:
            self.db_manager.drop_database(self.scratchpad_db)
        self._transition_to(PipelineState.SYNC)

    def _transition_to(self, new_state: PipelineState):
        logger.info(f"FSM Transition: {self.state.name} -> {new_state.name}")
        self.state = new_state

    # --- Implementacje Faz ---

    def _execute_auth(self):
        # Tutaj w przyszłości integracja z SmartMyVault
        logger.info("AUTH: Walidacja dostępów")

    def _execute_recon(self):
        # Tworzenie Scratchpad DB
        logger.info("RECON: Klonowanie środowiska")
        success = self.db_manager.duplicate_database(
            self.original_db, self.scratchpad_db
        )
        if not success:
            raise PipelineError("Nie udało się utworzyć Scratchpad DB")
            
        # Recon Odoo Environment
        if self.recon_engine:
            self.env_info = self.recon_engine.detect_version()
        else:
            self.env_info = EnvironmentInfo(
                odoo_version="unknown",
                edition="unknown",
                hosting_type="unknown"
            )
        logger.info(f"RECON EnvironmentInfo: {self.env_info}")

    def _execute_cognitive(self, intent: str, persona: str):
        # Wywołanie DecisionEngine
        logger.info("COGNITIVE: Uruchamianie protokołu ADP")
        self.adp_plan = self.decision_engine.evaluate(persona, intent, self.env_info)
        if "8_Plan" not in self.adp_plan:
            logger.warning(
                "Brak klucza 8_Plan w wyniku ADP, format może być niespójny."
            )

    def _execute_actuation(self):
        # Wykonanie wygenerowanego kodu/narzędzi na sklonowanej bazie
        logger.info(f"ACTUATION: Aplikowanie planu na bazie {self.scratchpad_db}")
        # Placeholder dla podłączania kodu MCP na scratchpadzie
        pass

    def _execute_sync(self, success: bool):
        # Integracja zmian do Live DB
        logger.info("SYNC: Zakończenie pracy i raportowanie")
        if success:
            # Gdy akcja zakończona pomyślnie, można zmergować lub zasygnalizować sukces
            logger.info(
                "Sukces. Środowisko robocze pozostawione do audytu przez człowieka."
            )
