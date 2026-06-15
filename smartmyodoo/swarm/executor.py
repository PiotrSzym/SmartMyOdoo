import json
import logging
import re
from typing import Dict, Any, Optional

from smartmyodoo.swarm.skills.skill_config import SkillConfig
from smartmyodoo.swarm.tools import TOOL_REGISTRY
from smartmyodoo.swarm.sandbox import SandboxManager

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
        pii: Optional[Any] = None,
    ):
        self.llm_client = llm_client
        self.chat_repo = chat_repo
        self.workspace_id = workspace_id
        self.session_id = session_id
        self.sandbox = sandbox
        # PiiMiddleware (S1.1): pseudonimizacja PII na granicy LLM. None = brak (np. testy jednostkowe).
        self.pii = pii

    def _anon(self, text: str) -> str:
        """Anonimizuj tekst PRZED wysłaniem do LLM (no-op gdy brak PiiMiddleware)."""
        if self.pii and isinstance(text, str) and text:
            return self.pii.anonymize(text, self.workspace_id)
        return text

    def _deanon(self, text: str) -> str:
        """Deanonimizuj tekst (tokeny → oryginał) dla użytkownika / wywołań narzędzi."""
        if self.pii and isinstance(text, str) and text:
            return self.pii.deanonymize(text, self.workspace_id)
        return text

    def _deanon_args(self, args: Any) -> Any:
        """Deanonimizuj argumenty narzędzia, by realnie odpytać Odoo prawdziwymi danymi."""
        if self.pii and isinstance(args, dict):
            return {
                k: (self._deanon(v) if isinstance(v, str) else v)
                for k, v in args.items()
            }
        return args

    def _get_audit_db(self):
        """Lazy-load DB session for audit logging."""
        try:
            from smartmyodoo.core.database import SessionLocal

            return SessionLocal()
        except Exception:
            return None

    def execute(
        self,
        skill_config: SkillConfig,
        message: str,
        phase_restrictions: Optional[list] = None,
    ) -> Dict[str, Any]:
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

        if phase_restrictions is not None:
            allowed_tools = [t for t in allowed_tools if t in phase_restrictions]

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
                for m in context:
                    if isinstance(m, dict) and isinstance(m.get("content"), str):
                        m["content"] = self._anon(m["content"])
                messages.extend(context)
            except Exception as e:
                logger.warning(f"Smart Context load failed: {e}")

        # S1.1: do LLM trafia pseudonimizowana wiadomość; oryginał idzie do historii.
        messages.append({"role": "user", "content": self._anon(message)})

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
                        # S1.1: przywróć realne dane do wywołania narzędzia (Odoo potrzebuje oryginału)
                        args = self._deanon_args(args)

                        # ── Sandbox: auto-enter before write tools ──
                        if (
                            self.sandbox
                            and self.sandbox.is_write_tool(func_name)
                            and not sandbox_activated
                        ):
                            logger.info(
                                f"🔒 Write tool detected: {func_name} — entering sandbox"
                            )
                            self.sandbox.enter_sandbox(original_db=self._get_odoo_db())
                            sandbox_activated = True

                        logger.info(f"Wywoływanie narzędzia: {func_name}({args})")
                        tools_used.add(func_name)

                        tool_result_str = ""
                        tool_success = True
                        if func_name in TOOL_REGISTRY:
                            try:
                                result = TOOL_REGISTRY[func_name]["callable"](**args)
                                # S1.1: anonimizuj wynik narzędzia (dane klientów) PRZED LLM
                                tool_result_str = self._anon(str(result))
                            except Exception as e:
                                tool_result_str = (
                                    f"Error executing {func_name}: {str(e)}"
                                )
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

                        messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "name": func_name,
                                "content": tool_result_str,
                            }
                        )
                else:
                    response_text = resp_message.content or ""
                    break
            else:
                response_text = (
                    "Błąd: Przekroczono maksymalną liczbę iteracji (tool loop)."
                )

        # ── Sandbox: exit successfully ──
        if sandbox_activated and self.sandbox:
            self.sandbox.exit_sandbox(success=True)

        # Close audit DB session
        if audit_db:
            try:
                audit_db.close()
            except Exception:
                pass

        # S1.1: przywróć realne dane w odpowiedzi dla użytkownika (LLM widział tylko tokeny)
        response_text = self._deanon(response_text)

        # Save assistant response to history
        self._save_chat(
            "assistant",
            response_text,
            {
                "tools_used": list(tools_used),
            },
        )

        # 5. Return result
        return {
            "response": response_text,
            "requires_human_override": skill_config.requires_human_override,
            "tools_used": list(tools_used),
        }

    async def execute_stream(
        self,
        skill_config: SkillConfig,
        message: str,
        phase_restrictions: Optional[list] = None,
    ):
        """
        Wykonuje zapytanie w trybie strumieniowym (Live Logs & Streaming).
        Zwraca asynchroniczny generator obiektów JSON.
        """
        import asyncio

        # 1. Red Flag Detection
        for flag in skill_config.red_flags:
            if re.search(flag, message, re.IGNORECASE):
                yield {"type": "error", "content": f"Red flag triggered: {flag}"}
                return

        # 2. Filter Tools
        allowed_tools = list(skill_config.allowed_tools)
        if skill_config.read_only and "odoo_create" in allowed_tools:
            allowed_tools.remove("odoo_create")

        if phase_restrictions is not None:
            allowed_tools = [t for t in allowed_tools if t in phase_restrictions]

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

        if self.chat_repo and self.session_id:
            try:
                context = self.chat_repo.get_smart_context(
                    self.workspace_id, self.session_id
                )
                for m in context:
                    if isinstance(m, dict) and isinstance(m.get("content"), str):
                        m["content"] = self._anon(m["content"])
                messages.extend(context)
            except Exception as e:
                logger.warning(f"Smart Context load failed: {e}")

        messages.append({"role": "user", "content": self._anon(message)})
        self._save_chat("user", message)

        response_text = ""
        tools_used = set()
        sandbox_activated = False
        audit_db = self._get_audit_db()

        if self.llm_client and hasattr(self.llm_client, "chat_stream"):
            max_iterations = 10
            for i in range(max_iterations):
                current_tool_calls = {}

                try:
                    stream = self.llm_client.chat_stream(
                        messages=messages,
                        tools=tools_schemas if tools_schemas else None,
                    )
                except Exception as e:
                    yield {"type": "error", "content": str(e)}
                    break

                full_message_content = ""
                for chunk in stream:
                    await asyncio.sleep(0)  # oddaj kontrolę do event loopa
                    if not chunk.choices:
                        continue

                    delta = chunk.choices[0].delta

                    if getattr(delta, "content", None):
                        full_message_content += delta.content
                        # S1.1: deanonimizuj token przed pokazaniem użytkownikowi (best-effort)
                        yield {"type": "token", "content": self._deanon(delta.content)}

                    if getattr(delta, "tool_calls", None):
                        for tc in delta.tool_calls:
                            tc_index = getattr(tc, "index", 0)
                            if tc_index not in current_tool_calls:
                                current_tool_calls[tc_index] = {
                                    "id": tc.id if hasattr(tc, "id") and tc.id else "",
                                    "type": "function",
                                    "function": {
                                        "name": tc.function.name
                                        if hasattr(tc.function, "name")
                                        and tc.function.name
                                        else "",
                                        "arguments": tc.function.arguments
                                        if hasattr(tc.function, "arguments")
                                        and tc.function.arguments
                                        else "",
                                    },
                                }
                            else:
                                if (
                                    hasattr(tc.function, "arguments")
                                    and tc.function.arguments
                                ):
                                    current_tool_calls[tc_index]["function"][
                                        "arguments"
                                    ] += tc.function.arguments
                                if hasattr(tc.function, "name") and tc.function.name:
                                    current_tool_calls[tc_index]["function"][
                                        "name"
                                    ] += tc.function.name

                if full_message_content:
                    response_text += full_message_content

                if not current_tool_calls:
                    msg_to_append: Dict[str, Any] = {
                        "role": "assistant",
                        "content": full_message_content,
                    }
                    messages.append(msg_to_append)
                    break

                # format tool calls for append
                formatted_tcs = []
                for idx, tc_data in current_tool_calls.items():

                    class _Function:
                        name = tc_data["function"]["name"]
                        arguments = tc_data["function"]["arguments"]

                    class _ToolCall:
                        id = tc_data["id"]
                        type = "function"
                        function = _Function()

                    formatted_tcs.append(_ToolCall())

                msg_to_append = {
                    "role": "assistant",
                    "content": full_message_content,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in formatted_tcs
                    ],
                }
                messages.append(msg_to_append)

                for tc in formatted_tcs:
                    func_name = tc.function.name
                    try:
                        args = json.loads(tc.function.arguments)
                    except Exception:
                        args = {}
                    args = self._deanon_args(args)

                    yield {
                        "type": "log",
                        "content": f"Wywoływanie narzędzia: {func_name}(...)",
                    }

                    if (
                        self.sandbox
                        and self.sandbox.is_write_tool(func_name)
                        and not sandbox_activated
                    ):
                        yield {
                            "type": "log",
                            "content": f"Uruchamiam bezpieczny Sandbox dla {func_name}",
                        }
                        self.sandbox.enter_sandbox(original_db=self._get_odoo_db())
                        sandbox_activated = True

                    tools_used.add(func_name)

                    tool_result_str = ""
                    tool_success = True
                    if func_name in TOOL_REGISTRY:
                        try:
                            result = TOOL_REGISTRY[func_name]["callable"](**args)
                            # S1.1: anonimizuj wynik narzędzia (dane klientów) PRZED LLM
                            tool_result_str = self._anon(str(result))
                        except Exception as e:
                            tool_result_str = f"Error executing {func_name}: {str(e)}"
                            tool_success = False
                            if sandbox_activated and self.sandbox:
                                self.sandbox.exit_sandbox(success=False)
                                sandbox_activated = False
                    else:
                        tool_result_str = f"Tool {func_name} not found."
                        tool_success = False

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

                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "name": func_name,
                            "content": tool_result_str,
                        }
                    )

            else:
                yield {
                    "type": "error",
                    "content": "Błąd: Przekroczono maksymalną liczbę iteracji (tool loop).",
                }

        if sandbox_activated and self.sandbox:
            self.sandbox.exit_sandbox(success=True)

        if audit_db:
            try:
                audit_db.close()
            except Exception:
                pass

        # S1.1: pełna deanonimizacja zapisanej/finalnej odpowiedzi (tokeny → oryginał)
        response_text = self._deanon(response_text)
        self._save_chat(
            "assistant",
            response_text,
            {
                "tools_used": list(tools_used),
            },
        )

        yield {"type": "done"}

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
