from enum import Enum, auto
import logging
from typing import Any, Dict, Optional, List
from .adp import DecisionEngine
from .db_manager import OdooDBManager
from .recon import EnvironmentRecon
from .models import EnvironmentInfo, SkillName

logger = logging.getLogger(__name__)


class PipelineState(Enum):
    AUTH = auto()
    RECON = auto()
    COGNITIVE = auto()
    ACTUATION = auto()
    SYNC = auto()


class PipelineError(Exception):
    """Error interrupting Pipeline execution."""

    pass


class ExecutionPipeline:
    """
    Maszyna Stanów (FSM) sterująca działaniem Agenta od autoryzacji do aktuacji,
    zawierająca mechanizm Scratchpad DB i rollback.
    """

    def __init__(
        self,
        db_manager: OdooDBManager,
        decision_engine: DecisionEngine,
        recon_engine: Optional[EnvironmentRecon] = None,
        executor: Optional[Any] = None,
        db_session: Optional[Any] = None,
        workspace_id: str = "default",
        on_transition_callback: Optional[Any] = None,
        dispatcher: Optional[Any] = None,
    ):
        self.state = PipelineState.AUTH
        self.db_manager = db_manager
        self.decision_engine = decision_engine
        self.recon_engine = recon_engine
        self.executor = executor
        self.db_session = db_session
        self.workspace_id = workspace_id
        self.on_transition_callback = on_transition_callback
        # S2.6: router intencji → dobór skilla per zadanie (koniec hardkodu ODOO_DEVELOPER)
        self.dispatcher = dispatcher
        self._skill_name: SkillName = SkillName.ODOO_DEVELOPER
        self._model: str = "openrouter/meta-llama/llama-3.1-8b-instruct"
        self._red_flags: List[str] = []

        # Kontekst wykonania
        self.original_db: str = ""
        self.scratchpad_db: str = ""
        self.adp_plan: Dict[str, Any] = {}
        self.env_info: Optional[EnvironmentInfo] = None
        self.credentials: Any = None
        self._rolled_back: bool = False

    def get_allowed_tools_for_phase(self, state: PipelineState) -> List[str]:
        """Return allowed tools for a given FSM phase.

        Policy (ADR-implied):
            AUTH:       no tools — authorization phase
            RECON:      read-only (search, schema, logs) — environment reconnaissance
            COGNITIVE:  no tools (intentional!) — LLM plans without tool-calls,
                        building an ADP plan based solely on collected RECON data
            ACTUATION:  full TOOL_REGISTRY set — plan execution
            SYNC:       no tools — finalization and reporting
        """
        from smartmyodoo.swarm.tools import TOOL_REGISTRY

        if state == PipelineState.RECON:
            return [
                "odoo_search",
                "odoo_schema",
                "search_knowledge_base",
                "read_odoo_log",
                "search_odoo_code",
            ]
        elif state == PipelineState.ACTUATION:
            return list(TOOL_REGISTRY.keys())
        return []  # COGNITIVE/AUTH/SYNC: intentionally empty — planning-only phase

    def _resolve_skill(self, intent: str):
        """S2.6: klasyfikuje intencję na właściwy SkillName + model + red_flags (z routingu).

        Fallback: ODOO_DEVELOPER, gdy brak dispatchera lub kategoria bez przypisanego skilla.
        """
        skill_name: SkillName = SkillName.ODOO_DEVELOPER
        model = self._model
        if self.dispatcher:
            try:
                dr = self.dispatcher.classify_intent(intent)
                if dr.skill_name:
                    skill_name = dr.skill_name
                if dr.recommended_model:
                    model = dr.recommended_model
            except Exception as e:
                logger.warning(f"Routing classify_intent failed: {e}")

        red_flags: List[str] = []
        try:
            from smartmyodoo.swarm.skills.registry import SKILL_REGISTRY

            cfg = SKILL_REGISTRY.get(skill_name)
            if cfg:
                red_flags = list(cfg.red_flags)
        except Exception as e:
            logger.warning(f"Skill registry load failed: {e}")

        return skill_name, model, red_flags

    def run(self, intent: str, persona: str, original_db: str, pin: str = "1111"):
        """Uruchamia pełen cykl FSM dla danego zadania."""
        self.original_db = original_db
        self.scratchpad_db = f"{original_db}_agent_scratchpad"
        # S2.6: dobierz skill na podstawie intencji (routing zamiast hardkodu)
        self._skill_name, self._model, self._red_flags = self._resolve_skill(intent)
        logger.info(
            f"ROUTING: intent → skill={self._skill_name.value}, model={self._model}"
        )

        try:
            self._transition_to(PipelineState.AUTH)
            self._execute_auth(pin)

            self._transition_to(PipelineState.RECON)
            self._execute_recon()

            self._transition_to(PipelineState.COGNITIVE)
            self._execute_cognitive(intent, persona)

            self._transition_to(PipelineState.ACTUATION)
            self._execute_actuation()

            self._transition_to(PipelineState.SYNC)
            self._execute_sync(success=True)

        except Exception as e:
            logger.error(f"Pipeline interrupted with error: {str(e)}")
            self.rollback()

    def rollback(self):
        """Rolls back state to SYNC, cleaning up the working environment."""
        logger.warning(f"Initiating Rollback for database {self.scratchpad_db}")
        self._rolled_back = True

        # B2.4: W przypadku błędu w ACTUATION zamykamy sandbox z sukcesem=False
        if (
            self.state == PipelineState.ACTUATION
            and hasattr(self, "executor")
            and self.executor
            and self.executor.sandbox
        ):
            self.executor.sandbox.exit_sandbox(success=False)

        if self.scratchpad_db:
            self.db_manager.drop_database(self.scratchpad_db)
        self._transition_to(PipelineState.SYNC)

    def _transition_to(self, new_state: PipelineState):
        old_state_name = self.state.name
        logger.info(f"FSM Transition: {old_state_name} -> {new_state.name}")
        self.state = new_state

        # 3.3 Audit Trail
        if self.db_session:
            try:
                from smartmyodoo.core.models import AuditLog

                audit = AuditLog(
                    workspace_id=self.workspace_id,
                    action="fsm_transition",
                    details=f"{old_state_name}→{new_state.name}, workspace={self.workspace_id}",
                )
                self.db_session.add(audit)
                self.db_session.commit()
            except Exception as e:
                logger.error(f"AuditLog failed: {e}")
                self.db_session.rollback()

        # 3.2 WebSocket event callback
        if self.on_transition_callback:
            try:
                self.on_transition_callback(new_state.name)
            except Exception as e:
                logger.error(f"Callback failed: {e}")

    # --- Implementacje Faz ---

    def _execute_auth(self, pin: str):
        from smartmyodoo.swarm.vault_auth import VaultAuthProvider

        logger.info("AUTH: Decrypting Odoo and AI secrets from Vault")
        logger.info("AUTH: Validating access in SmartMyVault")
        self.credentials = VaultAuthProvider.authenticate(pin)
        logger.info("AUTH: Credentials loaded successfully")

    def _execute_recon(self):
        # Create Scratchpad DB
        logger.info("RECON: Cloning environment")
        success = self.db_manager.duplicate_database(
            self.original_db, self.scratchpad_db
        )
        if not success:
            raise PipelineError("Failed to create Scratchpad DB")

        # Recon Odoo Environment
        if self.recon_engine:
            self.env_info = self.recon_engine.detect_version()
        else:
            self.env_info = EnvironmentInfo(
                odoo_version="unknown", edition="unknown", hosting_type="unknown"
            )
        logger.info(f"RECON EnvironmentInfo: {self.env_info}")

    def _execute_cognitive(self, intent: str, persona: str):
        logger.info("COGNITIVE: Planning operations")

        # 3.4 Token Governor Guard — estymacja pełnego kontekstu
        context_size = len(intent)
        if self.env_info:
            context_size += len(str(self.env_info))
        if self.adp_plan:
            context_size += len(str(self.adp_plan))
        # System prompt overhead (~500 tokens) + Smart Context history (~2000 tokens)
        estimated_tokens = (context_size // 4) + 2500
        if estimated_tokens > 128000:
            raise PipelineError(
                f"Context exceeds model limit: ~{estimated_tokens} tokens estimated"
            )

        if hasattr(self, "executor") and self.executor:
            # B2.2: executor.execute jako główny mechanizm
            from smartmyodoo.swarm.skills.skill_config import SkillConfig

            # W fazie COGNITIVE ograniczamy narzędzia
            allowed_tools = self.get_allowed_tools_for_phase(self.state)

            config = SkillConfig(
                name=self._skill_name,
                system_prompt="You are an assistant in FSM environment. Context: "
                + str(self.env_info),
                allowed_tools=allowed_tools,
                red_flags=self._red_flags,
                recommended_model=self._model,
            )
            # LLM tworzy ADP plan
            self.adp_plan = self.executor.execute(
                config, intent, phase_restrictions=allowed_tools
            )
        elif self.decision_engine:
            self.adp_plan = self.decision_engine.evaluate(
                persona, intent, self.env_info
            )
        else:
            self.adp_plan = {"response": "No decision engine available in COGNITIVE"}

    def _execute_actuation(self):
        logger.info(f"ACTUATION: Aplikowanie planu na bazie {self.scratchpad_db}")

        # B2.3: Sandbox — ustawiamy aktywny scratchpad na ten z RECON
        # (NIE klonujemy ponownie — RECON już utworzył scratchpad_db)
        if hasattr(self, "executor") and self.executor and self.executor.sandbox:
            logger.info(f"Sandbox: ustawiam aktywny scratchpad na {self.scratchpad_db}")
            self.executor.sandbox._active_scratchpad = self.scratchpad_db
            self.executor.sandbox._original_db = self.original_db

        if hasattr(self, "executor") and self.executor:
            from smartmyodoo.swarm.skills.skill_config import SkillConfig

            allowed_tools = self.get_allowed_tools_for_phase(self.state)
            credentials_info = (
                f"URL: {self.credentials.odoo_url}, DB: {self.credentials.odoo_db}"
                if self.credentials
                else ""
            )

            sys_prompt = f"ACTUATION: Zastosuj plan na środowisku. Context: {self.env_info}. {credentials_info} Plan: {self.adp_plan}"

            config = SkillConfig(
                name=self._skill_name,
                system_prompt=sys_prompt,
                allowed_tools=allowed_tools,
                red_flags=self._red_flags,
                recommended_model=self._model,
            )
            # Wykonanie planu (zapis)
            result = self.executor.execute(
                config, "Zastosuj plan", phase_restrictions=allowed_tools
            )
            logger.info(f"ACTUATION Result: {result}")

    def _execute_sync(self, success: bool):
        logger.info("SYNC: Finalizing and reporting")
        if success:
            logger.info("Success. Scratchpad preserved for human audit.")
        else:
            logger.warning(
                f"SYNC completed after rollback. Scratchpad '{self.scratchpad_db}' dropped."
            )
