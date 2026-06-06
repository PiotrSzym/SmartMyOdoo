import json
import logging
import re
from typing import Dict, Any, Optional

from smartmyodoo.swarm.skills.skill_config import SkillConfig
from smartmyodoo.swarm.tools import TOOL_REGISTRY
from smartmyodoo.swarm.sandbox import SandboxManager, WRITE_TOOLS

logger = logging.getLogger(__name__)

class RedFlagViolation(Exception):
    """Raised when a user intent matches a configured red flag for a skill."""
    pass

class SkillExecutor:
    def __init__(
        self,
        llm_client: Optional[Any] = None,
        chat_repo: Optional[Any] = None,
        workspace_id: str = "default",
        session_id: str = "",
        sandbox: Optional[SandboxManager] = None,
    ):
        self.llm_client = llm_client
        self.chat_repo = chat_repo
        self.workspace_id = workspace_id
        self.session_id = session_id
        self.sandbox = sandbox

    def _get_audit_db(self):
        """Lazy-load DB session for audit logging."""
        try:
            from smartmyodoo.core.database import SessionLocal
            return SessionLocal()
        except Exception:
            return None

    def execute(self, skill_config: SkillConfig, message: str) -> Dict[str, Any]:
        """
        Executes a given message against the skill configuration.
        Integrates: Chat History, Audit Trail, Sandbox.
        """
        # 1. Red Flag Detection
        for flag in skill_config.red_flags:
            if re.search(flag, message, re.IGNORECASE):
                raise RedFlagViolation(f"Red flag triggered: {flag}")

        # 2. Filter Tools
        allowed_tools = list(skill_config.allowed_tools)
        if skill_config.read_only and "odoo_create" in allowed_tools:
            allowed_tools.remove("odoo_create")
            
        tools_schemas = []
        for tool_name in allowed_tools:
            if tool_name in TOOL_REGISTRY:
                tools_schemas.append(TOOL_REGISTRY[tool_name]["schema"])
            else:
                logger.warning(f"Narzędzie '{tool_name}' nie istnieje w TOOL_REGISTRY.")

        # 3. Build messages with Smart Context
        messages = [
            {"role": "system", "content": skill_config.system_prompt},
        ]

        # Smart Context: załaduj skróty z poprzednich sesji
        if self.chat_repo and self.session_id:
            try:
                context = self.chat_repo.get_smart_context(
                    self.workspace_id, self.session_id
                )
                messages.extend(context)
            except Exception as e:
                logger.warning(f"Smart Context load failed: {e}")

        messages.append({"role": "user", "content": message})

        # Save user message to history
        self._save_chat("user", message)

        # 4. Call LLM
        response_text = ""
        tools_used = set()
        sandbox_activated = False
        audit_db = self._get_audit_db()
        
        if self.llm_client:
            max_iterations = 10
            for i in range(max_iterations):
                response = self.llm_client.chat(
                    messages=messages,
                    tools=tools_schemas if tools_schemas else None,
                )
                if not response or not getattr(response, "choices", None):
                    response_text = "LLM did not return a valid response."
                    break
                    
                resp_message = response.choices[0].message
                
                # Append LLM message to history
                msg_to_append = {"role": resp_message.role}
                if resp_message.content:
                    msg_to_append["content"] = resp_message.content
                if hasattr(resp_message, "tool_calls") and resp_message.tool_calls:
                    msg_to_append["tool_calls"] = [
                        tc.model_dump() if hasattr(tc, "model_dump") else dict(tc) 
                        for tc in resp_message.tool_calls
                    ]
                messages.append(msg_to_append)

                if hasattr(resp_message, "tool_calls") and resp_message.tool_calls:
                    for tool_call in resp_message.tool_calls:
                        func_name = tool_call.function.name
                        try:
                            args = json.loads(tool_call.function.arguments)
                        except Exception:
                            args = {}
                            
                        # ── Sandbox: auto-enter before write tools ──
                        if (
                            self.sandbox
                            and self.sandbox.is_write_tool(func_name)
                            and not sandbox_activated
                        ):
                            logger.info(f"🔒 Write tool detected: {func_name} — entering sandbox")
                            self.sandbox.enter_sandbox(
                                original_db=self._get_odoo_db()
                            )
                            sandbox_activated = True

                        logger.info(f"Wywoływanie narzędzia: {func_name}({args})")
                        tools_used.add(func_name)
                        
                        tool_result_str = ""
                        tool_success = True
                        if func_name in TOOL_REGISTRY:
                            try:
                                result = TOOL_REGISTRY[func_name]["callable"](**args)
                                tool_result_str = str(result)
                            except Exception as e:
                                tool_result_str = f"Error executing {func_name}: {str(e)}"
                                tool_success = False
                                # ── Sandbox: rollback on error ──
                                if sandbox_activated and self.sandbox:
                                    self.sandbox.exit_sandbox(success=False)
                                    sandbox_activated = False
                        else:
                            tool_result_str = f"Tool {func_name} not found."
                            tool_success = False

                        # ── Audit Trail: log every tool call ──
                        if audit_db:
                            try:
                                from smartmyodoo.core.audit import log_tool_call
                                log_tool_call(
                                    db=audit_db,
                                    workspace_id=self.workspace_id,
                                    tool_name=func_name,
                                    args=args,
                                    result=tool_result_str,
                                    success=tool_success,
                                )
                            except Exception as e:
                                logger.warning(f"Audit log failed: {e}")

                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "name": func_name,
                            "content": tool_result_str
                        })
                else:
                    response_text = resp_message.content or ""
                    break
            else:
                response_text = "Błąd: Przekroczono maksymalną liczbę iteracji (tool loop)."

        # ── Sandbox: exit successfully ──
        if sandbox_activated and self.sandbox:
            self.sandbox.exit_sandbox(success=True)

        # Close audit DB session
        if audit_db:
            try:
                audit_db.close()
            except Exception:
                pass

        # Save assistant response to history
        self._save_chat("assistant", response_text, {
            "tools_used": list(tools_used),
        })

        # 5. Return result
        return {
            "response": response_text,
            "requires_human_override": skill_config.requires_human_override,
            "tools_used": list(tools_used),
        }

    def _save_chat(self, role: str, content: str, metadata: Optional[dict] = None):
        """Zapisz wiadomość do persystentnej historii chatu."""
        if self.chat_repo and self.session_id:
            try:
                self.chat_repo.save_message(
                    workspace_id=self.workspace_id,
                    session_id=self.session_id,
                    role=role,
                    content=content,
                    metadata=metadata,
                )
            except Exception as e:
                logger.warning(f"Chat history save failed: {e}")

    def _get_odoo_db(self) -> str:
        """Pobierz nazwę bazy Odoo z ENV lub domyślną."""
        import os
        return os.environ.get("ODOO_DB", "odoo_main")

