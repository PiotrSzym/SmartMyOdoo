import json
import logging
import os
import re
from typing import Dict, Any, Optional

from smartmyodoo.swarm.skills.skill_config import SkillConfig
from smartmyodoo.swarm.tools import TOOL_REGISTRY
from smartmyodoo.swarm.sandbox import SandboxManager, WRITE_TOOLS

# WRITE-02 T2: komunikat zwracany modelowi, gdy próbuje zapisu w trybie tylko-odczyt (🟢).
READ_MODE_BLOCK_MSG = (
    "🟢 TRYB ODCZYTU — zapis ZABLOKOWANY. Użytkownik jest w trybie tylko-do-odczytu, "
    "więc NIE utworzono żadnej zmiany ani propozycji. Poproś użytkownika, aby przełączył "
    "kłódkę w prawym górnym rogu czatu na TRYB EDYCJI 🔴 (potwierdza PIN-em) — dopiero "
    "wtedy przygotujesz propozycję zmiany. NIE twierdź, że cokolwiek zmieniłeś."
)

logger = logging.getLogger(__name__)

# TRUST-03 T1 (D1): ile ostatnich tur BIEŻĄCEJ sesji odtwarzać do LLM (Buffer Window).
# Dziś LLM nie dostawał ich wcale (get_smart_context pomija bieżącą sesję) — stąd
# gubienie kontekstu („price list" → cennik). ENV-override: CHAT_HISTORY_TURNS.
_HISTORY_TURNS = int(os.environ.get("CHAT_HISTORY_TURNS", "6"))

# TRUST-03 T4 (D6): po deanonymize w finalnej odpowiedzi mogą zostać NIEROZPOZNANE
# tokeny maski — gdy model renumerował token (np. napisał <PERSON_1> zamiast utworzonego
# <PERSON_3>), deanonymize go nie trafi. Zamieniamy takie resztki na „[zamaskowane]",
# żeby user nie zobaczył surowego tokenu systemowego. Stosowane TYLKO na finalnym
# reply (NIE na argumentach narzędzi — tam token musi zostać nienaruszony).
_LEFTOVER_TOKEN_RE = re.compile(r"<[A-Z][A-Z_]*_\d+>")


def _mask_leftover_tokens(text: str) -> str:
    if not isinstance(text, str) or not text:
        return text
    return _LEFTOVER_TOKEN_RE.sub("[zamaskowane]", text)


# TRUST-01 T1 + TRUST-02 T1 (decyzja D1): confab-guard PII — VERBATIM-ONLY.
# Dane Odoo trafiają do LLM po pseudonimizacji ('RMO <PERSON_2>'). Bez reguły
# model ZGADYWAŁ wartość spod maski ('RMO Billing Type'). TRUST-02 usuwa ścieżkę
# "[zamaskowane]" (blokowała deanonymize i odbierała lokalnemu userowi prawdziwą
# nazwę) oraz precyzuje, że TYLKO token <TYP_numer> jest maską — żeby literówka
# ('jkie') nie była brana za maskę. Model ma cytować token DOSŁOWNIE; warstwa
# lokalna (_deanonymize) podmieni go na realną wartość dla usera (Sekcja D:
# chmura nadal widzi tylko token).
_GUARD_MARKER = "ZASADA DANYCH ZAMASKOWANYCH"
PII_CONFAB_GUARD = (
    f"\n\n--- {_GUARD_MARKER} (BEZWZGLĘDNA) ---\n"
    "Maska to WYŁĄCZNIE token w formacie <TYP_numer> w nawiasach ostrokątnych, np. "
    "<PERSON_1>, <LOCATION_2>, <ORGANIZATION_1>, <EMAIL_ADDRESS_1>, <NIP_1>, <PESEL_1>. "
    "To pseudonimy realnych danych. ZASADY:\n"
    "1. Token cytuj ZAWSZE DOSŁOWNIE, w niezmienionej formie (np. <PERSON_1>). Warstwa "
    "lokalna sama podmieni go na prawdziwą wartość dla użytkownika — to NIE Twoje zadanie.\n"
    "2. NIGDY nie zgaduj, nie rozwijaj ani nie wymyślaj wartości spod tokenu. Zmyślenie "
    "nazwy w miejsce tokenu to błąd krytyczny.\n"
    "3. NIE zastępuj tokenu zwrotem \"[zamaskowane]\" ani opisem — to blokuje podmianę na "
    "prawdziwą wartość. Zostaw token dokładnie jak jest.\n"
    "4. Zwykły wyraz, literówka albo fraza użytkownika, która NIE ma formy <TYP_numer>, "
    "NIE jest maską — traktuj ją normalnie; nie twierdź, że jest zamaskowana."
)


# TRUST-04 T1: standing rule — filtrowanie po OSOBIE idzie przez resolve_person,
# bo LLM widzi zamaskowane nazwiska i nie dopasuje ich do user_id (stąd „piotr sz"
# → zły Piotr). resolve_person szuka serwerowo po realnych nazwach i zwraca user_id.
PEOPLE_RESOLVE_RULE = (
    "\n\n--- ROZPOZNAWANIE OSÓB (Odoo) ---\n"
    "Gdy masz filtrować rekordy po OSOBIE (np. szanse/zadania „dla X”, „przypisane do "
    "X”, „użytkownika X”), NAJPIERW wywołaj narzędzie resolve_person z tą nazwą, by "
    "dostać prawdziwe user_id. NIGDY nie zgaduj user_id z zamaskowanych nazw "
    "(<PERSON_x>). Gdy resolve_person zwróci 1 użytkownika — użyj jego uid w filtrze "
    "user_id. Gdy zwróci kilku — zapytaj użytkownika, cytując zwrócone tokeny nazw "
    "DOSŁOWNIE (zostaną podmienione na prawdziwe nazwiska)."
)


# WRITE-02 T3: anty-konfabulacja zapisu. Narzędzia write (odoo_create/update/delete)
# zwracają PROPOZYCJĘ (Shadow Mode), a NIE wykonany zapis. Model nie może meldować
# „gotowe/zmieniłem” — realna zmiana następuje dopiero po zatwierdzeniu (apply+PIN).
WRITE_REPORT_RULE = (
    "\n\n--- ZAPIS DO ODOO (BEZWZGLĘDNA) ---\n"
    "Narzędzia zapisu (odoo_create, odoo_update, odoo_delete) NIE zmieniają Odoo od "
    "razu — tworzą PROPOZYCJĘ oczekującą na zatwierdzenie (Shadow Mode). Dlatego:\n"
    "1. NIGDY nie pisz „gotowe / zmieniłem / zmieniono / zapisałem / usunąłem” po "
    "wywołaniu narzędzia zapisu. To NIEPRAWDA — zmiana nie jest jeszcze wykonana.\n"
    "2. Powiedz, że PRZYGOTOWAŁEŚ propozycję i czeka na zatwierdzenie przyciskiem "
    "„💾 Zapisz na Odoo” (wymaga PIN). Krótko opisz, co zmieni.\n"
    "3. Gdy dostaniesz komunikat o TRYBIE ODCZYTU (🟢) — NIE udawaj, że coś zrobiłeś; "
    "poproś użytkownika, by przełączył kłódkę na TRYB EDYCJI 🔴."
)


def build_system_prompt(base_prompt: str) -> str:
    """Składa prompt systemowy: prompt skilla + confab-guard PII + reguła osób +
    reguła zapisu (idempotentnie). SSoT — używane przez execute i execute_stream.
    """
    base = base_prompt or ""
    if _GUARD_MARKER in base:
        # Guard już doklejony (np. prompt budowany ponownie) — nie dubluj.
        return base
    return base + PII_CONFAB_GUARD + PEOPLE_RESOLVE_RULE + WRITE_REPORT_RULE


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
        scope: Optional[Any] = None,
        edit_mode: bool = False,
    ):
        self.llm_client = llm_client
        self.chat_repo = chat_repo
        self.workspace_id = workspace_id
        self.session_id = session_id
        self.sandbox = sandbox
        # WRITE-02 T2: stan kłódki UI (🟢 read / 🔴 edit). W trybie read write-tool
        # jest deterministycznie blokowany (autoryzacja = świadome przełączenie 🔴+PIN).
        self.edit_mode = edit_mode
        # WRITE-02 T4: ostatnia propozycja utworzona w pętli narzędzi (→ karta w czacie).
        self.last_proposal: Optional[Dict[str, Any]] = None
        # PiiMiddleware (S1.1): pseudonimizacja PII na granicy LLM. None = brak (np. testy jednostkowe).
        self.pii = pii
        # TRUST-01 T5 (D5): ConversationScope — pamięć project_id między turami.
        # None = brak (testy jednostkowe / brak pamięci zakresu).
        self.scope = scope
        # S2.3: stan przekierowania bazy Odoo na scratchpad (izolacja sandbox)
        self._saved_db: Optional[str] = None
        self._db_redirected = False

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

    def _capture_scope(self, func_name: str, args: Any) -> None:
        """TRUST-01 T5: wyłuskaj project_id z domeny zapytania Odoo i zapamiętaj go.

        Domena bywa stringiem w składni Pythona/JSON — parsujemy tolerancyjnie
        (ast.literal_eval). No-op gdy brak trackera/zakresu (testy jednostkowe)."""
        if self.scope is None or not isinstance(args, dict):
            return
        if "odoo_search" not in func_name and "search" not in func_name:
            return
        domain = args.get("domain")
        if isinstance(domain, str):
            import ast

            try:
                domain = ast.literal_eval(domain)
            except Exception:
                return
        if isinstance(domain, (list, tuple)):
            try:
                self.scope.capture_domain(
                    self.workspace_id, self.session_id, domain
                )
            except Exception as e:  # noqa: BLE001
                logger.warning(f"Scope capture failed: {e}")

    def _enforce_scope(self, func_name: str, args: Any, message: str) -> None:
        """TRUST-02 T2: deterministycznie dokleja project_id aktywnego zakresu do
        domeny zapytania o zadania (mutuje args in-place). No-op bez trackera/zakresu."""
        if self.scope is None:
            return
        try:
            if self.scope.enforce_scope(
                self.workspace_id, self.session_id, func_name, args, message
            ):
                logger.info(f"Scope enforce: doklejono project_id do {func_name}")
        except Exception as e:  # noqa: BLE001 — egzekwowanie zakresu to ulepszenie, nie bloker
            logger.warning(f"Scope enforce failed: {e}")

    def _capture_provenance(self, prov: Any, func_name: str, tool_result_str: str) -> None:
        """TRUST-01 T6: wyłuskaj 'count' (liczba rekordów) oraz wersję Odoo z wyniku
        narzędzia, by zbudować stopkę provenance. Tolerancyjny — błędy są nieistotne."""
        if not isinstance(tool_result_str, str) or not tool_result_str:
            return
        try:
            data = json.loads(tool_result_str)
        except Exception:
            return
        if isinstance(data, dict):
            cnt = data.get("count")
            if isinstance(cnt, int):
                prov.record_count(cnt)
            # Wersja Odoo, jeśli narzędzie ją zwraca (np. odoo_schema/version).
            ver = data.get("odoo_version") or data.get("version")
            if ver:
                prov.set_version(ver)

    def _capture_records(self, func_name: str, args: Any, tool_result_str: str) -> None:
        """TRUST-03 T2: wyłuskaj POKAZANE rekordy (id+tytuł) z wyniku search → kotwica
        encji do disambiguacji nazw. Wynik narzędzia jest już zanonimizowany."""
        if self.scope is None or "search" not in (func_name or ""):
            return
        if not isinstance(tool_result_str, str) or not tool_result_str:
            return
        try:
            data = json.loads(tool_result_str)
        except Exception:
            return
        if isinstance(data, dict):
            records = data.get("records")
        elif isinstance(data, list):
            records = data
        else:
            return
        model = (args or {}).get("model_name") or (args or {}).get("model") or ""
        try:
            self.scope.capture_records(
                self.workspace_id, self.session_id, model, records
            )
        except Exception as e:  # noqa: BLE001 — kotwica to ulepszenie, nie bloker
            logger.warning(f"Record capture failed: {e}")

    def _capture_proposal(
        self, func_name: str, args: Any, tool_result_str: str, tool_success: bool
    ) -> None:
        """WRITE-02 T4: przechwyć propozycję utworzoną przez write-tool, by `handle_chat`
        zwrócił ją jako kartę (diff + 💾 Zapisz). Czytamy proposal_id z wyniku narzędzia
        („… ID: xxxx”) i model/method/values z argumentów (już zdeanonimizowanych)."""
        if func_name not in WRITE_TOOLS or not tool_success:
            return
        if not isinstance(tool_result_str, str):
            return
        m = re.search(r"ID:\s*([A-Za-z0-9_-]+)", tool_result_str)
        if not m:
            return
        a = args if isinstance(args, dict) else {}
        method = {
            "odoo_create": "create",
            "odoo_update": "update",
            "odoo_delete": "delete",
        }.get(func_name, "update")
        values: Dict[str, Any] = {}
        vj = a.get("values_json")
        if isinstance(vj, str):
            try:
                values = json.loads(vj)
            except Exception:
                values = {}
        elif isinstance(vj, dict):
            values = vj
        self.last_proposal = {
            "proposal_id": m.group(1),
            "model": a.get("model_name") or a.get("model") or "",
            "method": method,
            "record_id": a.get("record_id"),
            "values": values,
            "reason": a.get("reason") or "",
        }

    def _enter_db_redirect(self, scratchpad: str) -> None:
        """S2.3: przekieruj narzędzia Odoo na scratchpad (przez ODOO_DB), zapisując oryginał."""
        self._saved_db = os.environ.get("ODOO_DB")
        os.environ["ODOO_DB"] = scratchpad
        self._db_redirected = True

    def _restore_db_redirect(self) -> None:
        """S2.3: przywróć oryginalną bazę po wyjściu z sandboxa."""
        if not self._db_redirected:
            return
        if self._saved_db is None:
            os.environ.pop("ODOO_DB", None)
        else:
            os.environ["ODOO_DB"] = self._saved_db
        self._db_redirected = False

    def _get_audit_db(self):
        """Lazy-load DB session for audit logging."""
        try:
            from smartmyodoo.core.database import SessionLocal

            return SessionLocal()
        except Exception:
            return None

    # ── S3.2: WSPÓLNE HELPERY POLITYK (SSoT dla execute i execute_stream) ──
    # Caller decyduje o PREZENTACJI (raise/yield, logger/yield); polityka jest jedna.

    def _first_red_flag(self, skill_config: SkillConfig, message: str) -> Optional[str]:
        """Zwraca pierwszą dopasowaną red flag (lub None). Detektor — bez efektów ubocznych."""
        for flag in skill_config.red_flags:
            if re.search(flag, message, re.IGNORECASE):
                return flag
        return None

    def _prepare_tools(
        self, skill_config: SkillConfig, phase_restrictions: Optional[list]
    ) -> tuple:
        """Filtr narzędzi (read_only zdejmuje odoo_create + restrykcje fazy) + budowa schematów.

        Zwraca (allowed_tools, tools_schemas) — identycznie dla obu ścieżek.
        """
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
        return allowed_tools, tools_schemas

    def _build_initial_messages(self, skill_config: SkillConfig, message: str) -> list:
        """System prompt + Smart Context (anonimizowany) + wiadomość user (anon) + zapis do historii."""
        messages = [
            # TRUST-01 T1: dokładamy confab-guard PII do promptu skilla.
            {"role": "system", "content": build_system_prompt(skill_config.system_prompt)},
        ]
        # TRUST-03 T2+T4 (Entity Memory): jawna kotwica — aktywny projekt + ostatnio
        # pokazane rekordy + reguła disambiguacji (price list↔cennik). Zastępuje
        # plaster scope_hint (TRUST-01 T5) — jest jego nadzbiorem. Przeżywa przycięcie
        # historii (T3). Deterministyczny filtr domeny nadal robi enforce_scope (T2).
        if self.scope is not None:
            try:
                block = self.scope.context_block(self.workspace_id, self.session_id)
                if block:
                    insert_at = (
                        1 if messages and messages[0].get("role") == "system" else 0
                    )
                    messages.insert(insert_at, {"role": "system", "content": block})
            except Exception as e:  # noqa: BLE001
                logger.warning(f"Context block injection failed: {e}")
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

        # TRUST-03 T1+T3: odtwórz historię BIEŻĄCEJ sesji do LLM (Summary Buffer):
        # ostatnie N tur dosłownie + streszczenie starszych tur (gdy rozmowa dłuższa).
        # Zanonimizowane jak bieżąca wiadomość. Bez tego model gubił kontekst.
        if self.chat_repo and self.session_id and _HISTORY_TURNS > 0:
            try:
                hist = self.chat_repo.get_history_context(
                    self.session_id, max_turns=_HISTORY_TURNS
                )
                for m in hist:
                    if isinstance(m, dict) and isinstance(m.get("content"), str):
                        messages.append(
                            {"role": m["role"], "content": self._anon(m["content"])}
                        )
            except Exception as e:  # noqa: BLE001 — historia to ulepszenie, nie bloker
                logger.warning(f"Conversation history load failed: {e}")

        # S1.1: do LLM trafia pseudonimizowana wiadomość; oryginał idzie do historii.
        messages.append({"role": "user", "content": self._anon(message)})
        self._save_chat("user", message)
        return messages

    def _should_sandbox(self, func_name: str, sandbox_activated: bool) -> bool:
        """Czy dla tego narzędzia trzeba (i można) wejść w sandbox — predykat."""
        return bool(
            self.sandbox
            and self.sandbox.is_write_tool(func_name)
            and not sandbox_activated
        )

    def _enter_sandbox_fail_closed(self) -> tuple:
        """S2.3: wejście w sandbox z fail-closed + redirect ODOO_DB na scratchpad.

        Zwraca (blocked, sandbox_activated). blocked=True → brak izolacji przy włączonym
        sandboxie (zapis MA być zablokowany, zero zapisu na produkcji).
        Wołane tylko po _should_sandbox()==True (gwarantuje self.sandbox is not None).
        """
        sandbox = self.sandbox
        if sandbox is None:  # obrona; nie powinno się zdarzyć (guard w _should_sandbox)
            return False, False
        try:
            scratchpad = sandbox.enter_sandbox(original_db=self._get_odoo_db())
        except RuntimeError as e:
            # np. brak ODOO_MASTER_PASSWORD — fail-closed, nie crash requestu
            logger.warning(f"Sandbox fail-closed: {e}")
            scratchpad = None
        if sandbox.enabled and not scratchpad:
            return True, False  # FAIL-CLOSED: brak izolacji → nie wykonuj zapisu
        if scratchpad:
            self._enter_db_redirect(scratchpad)
        return False, True

    def _invoke_tool(
        self, func_name: str, args: Any, blocked: bool, sandbox_activated: bool
    ) -> tuple:
        """Wywołanie narzędzia z TOOL_REGISTRY + anonimizacja wyniku + rollback na błędzie.

        Zwraca (tool_result_str, tool_success, sandbox_activated).
        """
        if blocked:
            return (
                "❌ Sandbox fail-closed: nie udało się utworzyć izolacji — "
                "operacja zapisu zablokowana (zero zapisu na produkcji).",
                False,
                sandbox_activated,
            )
        if func_name in TOOL_REGISTRY:
            try:
                result = TOOL_REGISTRY[func_name]["callable"](**args)
                # S1.1: anonimizuj wynik narzędzia (dane klientów) PRZED LLM
                return self._anon(str(result)), True, sandbox_activated
            except Exception as e:
                # ── Sandbox: rollback on error ──
                if sandbox_activated and self.sandbox:
                    self.sandbox.exit_sandbox(success=False)
                    self._restore_db_redirect()
                    sandbox_activated = False
                return (
                    f"Error executing {func_name}: {str(e)}",
                    False,
                    sandbox_activated,
                )
        return f"Tool {func_name} not found.", False, sandbox_activated

    def _audit_tool_call(
        self, audit_db: Any, func_name: str, args: Any, result: str, success: bool
    ) -> None:
        """Audit Trail: zapis każdego wywołania narzędzia (best-effort)."""
        if not audit_db:
            return
        try:
            from smartmyodoo.core.audit import log_tool_call

            log_tool_call(
                db=audit_db,
                workspace_id=self.workspace_id,
                tool_name=func_name,
                args=args,
                result=result,
                success=success,
            )
        except Exception as e:
            logger.warning(f"Audit log failed: {e}")

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
        # 1. Red Flag Detection (S3.2: wspólny detektor; tu prezentacja = raise)
        flag = self._first_red_flag(skill_config, message)
        if flag:
            raise RedFlagViolation(f"Red flag triggered: {flag}")

        # 2. Filter Tools (S3.2: wspólny helper)
        allowed_tools, tools_schemas = self._prepare_tools(
            skill_config, phase_restrictions
        )

        # 3. Build messages with Smart Context (S3.2: wspólny helper)
        messages = self._build_initial_messages(skill_config, message)

        # 4. Call LLM
        response_text = ""
        tools_used = set()
        sandbox_activated = False
        audit_db = self._get_audit_db()
        # TRUST-01 T6: akumulator provenance (rekordy + maski PII) dla stopki.
        from smartmyodoo.swarm.provenance import ProvenanceAccumulator

        prov = ProvenanceAccumulator(pii=self.pii, workspace_id=self.workspace_id)

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

                        # WRITE-03 T2: narzędzia zapisu MUSZĄ nieść REALNY workspace
                        # (LLM go nie przekazuje → propozycja lądowałaby jako „default”,
                        # a apply trafiałby w złą instancję Odoo). Wstrzykujemy go tu,
                        # by create_proposal otagował propozycję właściwą przestrzenią.
                        if (
                            func_name in WRITE_TOOLS
                            and isinstance(args, dict)
                            and self.workspace_id
                        ):
                            args["workspace_id"] = self.workspace_id

                        # TRUST-02 T2: deterministycznie utrzymaj zakres projektu
                        # (doklej project_id), zanim narzędzie wystartuje.
                        self._enforce_scope(func_name, args, message)
                        # TRUST-01 T5: zapamiętaj project_id z domeny zapytania Odoo,
                        # by follow-up w tej samej sesji dziedziczył zakres.
                        self._capture_scope(func_name, args)

                        # ── WRITE-02 T2: read-mode write-guard (DETERMINISTYCZNY) ──
                        # W trybie 🟢 (read) NIE wykonujemy narzędzia zapisu — model dostaje
                        # prośbę o przełączenie na 🔴. Nie ufamy modelowi: blok jest tu, nie w
                        # prompcie. Pomijamy inwokację (zero propozycji w trybie odczytu).
                        if func_name in WRITE_TOOLS and not self.edit_mode:
                            logger.info(
                                f"🟢 Read-mode: zapis {func_name} zablokowany "
                                "(brak trybu edycji)"
                            )
                            tools_used.add(func_name)
                            self._audit_tool_call(
                                audit_db, func_name, args, READ_MODE_BLOCK_MSG, False
                            )
                            messages.append(
                                {
                                    "role": "tool",
                                    "tool_call_id": tool_call.id,
                                    "name": func_name,
                                    "content": READ_MODE_BLOCK_MSG,
                                }
                            )
                            continue

                        # ── Sandbox (S2.3): fail-closed + redirect (S3.2: wspólne helpery) ──
                        blocked = False
                        if self._should_sandbox(func_name, sandbox_activated):
                            logger.info(
                                f"🔒 Write tool detected: {func_name} — entering sandbox"
                            )
                            blocked, sandbox_activated = (
                                self._enter_sandbox_fail_closed()
                            )

                        logger.info(f"Wywoływanie narzędzia: {func_name}({args})")
                        tools_used.add(func_name)

                        tool_result_str, tool_success, sandbox_activated = (
                            self._invoke_tool(
                                func_name, args, blocked, sandbox_activated
                            )
                        )

                        self._audit_tool_call(
                            audit_db, func_name, args, tool_result_str, tool_success
                        )

                        # TRUST-01 T6: zbierz liczbę rekordów + wersję Odoo z wyniku.
                        self._capture_provenance(prov, func_name, tool_result_str)
                        # TRUST-03 T2: zapamiętaj pokazane rekordy (kotwica encji).
                        self._capture_records(func_name, args, tool_result_str)
                        # WRITE-02 T4: przechwyć propozycję (→ karta z diffem w czacie).
                        self._capture_proposal(
                            func_name, args, tool_result_str, tool_success
                        )

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
            self._restore_db_redirect()

        # Close audit DB session
        if audit_db:
            try:
                audit_db.close()
            except Exception:
                pass

        # S1.1: przywróć realne dane w odpowiedzi dla użytkownika (LLM widział tylko tokeny)
        # TRUST-03 T4/D6: + zamaskuj nierozpoznane tokeny (renumeracja modelu).
        response_text = _mask_leftover_tokens(self._deanon(response_text))

        # TRUST-01 T6: doklej stopkę provenance (źródło/wersja/rekordy/maski), gdy
        # tura dotykała danych Odoo. Tylko liczniki — bez wartości (0G).
        from smartmyodoo.swarm.provenance import append_provenance

        footer = prov.footer()
        response_text = append_provenance(response_text, footer)

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
            "provenance": footer,
            # WRITE-02 T4: propozycja utworzona w tej turze (→ karta w czacie) lub None.
            "proposal": self.last_proposal,
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

        # 1. Red Flag Detection (S3.2: wspólny detektor; tu prezentacja = yield error)
        flag = self._first_red_flag(skill_config, message)
        if flag:
            yield {"type": "error", "content": f"Red flag triggered: {flag}"}
            return

        # 2. Filter Tools (S3.2: wspólny helper)
        allowed_tools, tools_schemas = self._prepare_tools(
            skill_config, phase_restrictions
        )

        # 3. Build messages with Smart Context (S3.2: wspólny helper)
        messages = self._build_initial_messages(skill_config, message)

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
                    # TRUST-02 T2: deterministyczne utrzymanie zakresu projektu.
                    self._enforce_scope(func_name, args, message)
                    self._capture_scope(func_name, args)

                    yield {
                        "type": "log",
                        "content": f"Wywoływanie narzędzia: {func_name}(...)",
                    }

                    # S2.3 (parytet streamingu): fail-closed + redirect (S3.2: wspólne helpery)
                    blocked = False
                    if self._should_sandbox(func_name, sandbox_activated):
                        yield {
                            "type": "log",
                            "content": f"Uruchamiam bezpieczny Sandbox dla {func_name}",
                        }
                        blocked, sandbox_activated = self._enter_sandbox_fail_closed()

                    tools_used.add(func_name)

                    tool_result_str, tool_success, sandbox_activated = (
                        self._invoke_tool(func_name, args, blocked, sandbox_activated)
                    )

                    self._audit_tool_call(
                        audit_db, func_name, args, tool_result_str, tool_success
                    )

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
            self._restore_db_redirect()

        if audit_db:
            try:
                audit_db.close()
            except Exception:
                pass

        # S1.1: pełna deanonimizacja zapisanej/finalnej odpowiedzi (tokeny → oryginał)
        # TRUST-03 T4/D6: + zamaskuj nierozpoznane tokeny (renumeracja modelu).
        response_text = _mask_leftover_tokens(self._deanon(response_text))
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
