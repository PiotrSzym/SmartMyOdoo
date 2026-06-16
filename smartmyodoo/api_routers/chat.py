"""FIX-02 S3.1b: domena `chat` wydzielona z God Module api.py.

Endpointy: GET /api/skills, POST /api/chat, POST /api/pipeline/run, WS /api/chat/stream.
Zależności (dispatcher, PII) z `chat_deps` — NIE z api.py (zero cyklu, patrz S3.4).
governor bezpośrednio z mcp.token_governor; auth z api_deps. Zachowanie bez zmian.
"""

import os
import json
from typing import List, Tuple

from pydantic import BaseModel
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from smartmyodoo.core.database import get_db
from smartmyodoo.vault import vault
from smartmyodoo.swarm.models import ChatRequest, ChatResponse, ChatProposalData
from smartmyodoo.mcp.token_governor import governor as _token_governor
from smartmyodoo.api_deps import require_auth, get_auth_key
from smartmyodoo.chat_deps import dispatcher, get_pii as _get_pii

router = APIRouter(tags=["chat"])


class PipelineRunRequest(BaseModel):
    message: str
    workspace_id: str = "default"
    session_id: str = ""
    selected_skills: List[str] = []
    use_pipeline: bool = True


@router.get("/api/skills")
async def get_skills(
    auth_data: Tuple[bytes, str, str] = Depends(require_auth),
):
    from smartmyodoo.swarm.skills.registry import SKILL_REGISTRY

    skills = []
    # These match the icons and descriptions provided in the SkillPanel for UI consistency
    ui_defaults = {
        "ODOO_BUSINESS_ANALYST": {
            "icon": "📊",
            "name": "Business Analyst",
            "desc": "Standard First — konfiguracja",
            "tooltip": 'Główny strateg i architekt procesów. Skupia się na analizie biznesowej, architekturze danych i konfiguracji Standard Odoo bez pisania kodu. Wzywaj go jako pierwszego, gdy projektujesz nowy moduł lub chcesz zoptymalizować działanie firmy w oparciu o natywne funkcjonalności. Przykład: "Zaprojektuj proces obiegu faktur wykorzystując natywne moduły księgowości, bez pisania własnego kodu."',
        },
        "ODOO_DEVELOPER": {
            "icon": "💻",
            "name": "Developer",
            "desc": "_inherit mandatory, no core mod",
            "tooltip": 'Główny architekt techniczny. Odpowiada za bezpieczne modyfikacje kodu za pomocą dziedziczenia (`_inherit`), dbając o absolutny brak modyfikacji rdzenia (core) systemu. Koduje w Pythonie, optymalizuje modele ORM i dba o czystą architekturę tworzonych aplikacji. Przykład: "Stwórz nowy model dziedziczący po sale.order i dodaj pole obliczające marżę."',
        },
        "ODOO_DEVOPS_GITHUB": {
            "icon": "🚀",
            "name": "DevOps/GitHub",
            "desc": "Staging Isolation, Feature Branches",
            "tooltip": 'Dowódca infrastruktury i wdrożeń. Zarządza repozytorium GitHub, strategią gałęzi (feature branches) i procesami CI/CD. Gwarantuje stabilność poprzez rygorystyczne używanie środowisk izolowanych (Staging) przed każdą produkcyjną zmianą. Przykład: "Wydziel bieżące zmiany do nowej gałęzi feature/invoice-approval i przygotuj PR."',
        },
        "ODOO_SH_LOGS": {
            "icon": "📋",
            "name": "SH Logs",
            "desc": "Tracebacki bottom-up",
            "tooltip": 'Specjalista od środowiska Odoo.sh i analizy błędów krytycznych. Jego tajną bronią jest czytanie tracebacków metodą "bottom-up" (od dołu do góry), co pozwala mu w mgnieniu oka zlokalizować korzeń każdego błędu serwera. Przykład: "Sprawdź w logach Odoo.sh dlaczego o 14:00 użytkownicy dostawali błąd 500."',
        },
        "ODOO_AUDIT_HISTORY": {
            "icon": "🔍",
            "name": "Audit History",
            "desc": "Chatter tracking via mail.message",
            "tooltip": 'Inspektor śledczy historii zmian. Biegle porusza się w architekturze wewnętrznego komunikatora (chatter) w Odoo, wykorzystując relacje do `mail.message`, aby śledzić kto, co i kiedy zmienił w systemie. Przykład: "Prześledź chatter z ostatnich 3 dni, aby znaleźć użytkownika, który omyłkowo zmienił stawkę VAT."',
        },
        "ODOO_CRUD": {
            "icon": "🗄️",
            "name": "CRUD",
            "desc": "Magic Tuples (0,0,{})",
            "tooltip": 'Mistrz manipulacji danymi i zapytań w Odoo. Zna na pamięć logikę struktur relacyjnych, w tym specyfikę operacji "Magic Tuples" (np. `(0, 0, {})` dla tworzenia nowych rekordów czy `(4, id)` dla łączenia w Many2many). Przykład: "Napisz kod aktualizujący relację One2many używając (0, 0, {}) do dodania nowych linii."',
        },
        "ODOO_ETL_MANAGER": {
            "icon": "📦",
            "name": "ETL Manager",
            "desc": "Batching 200 rek/req",
            "tooltip": 'Inżynier wielkich migracji i importów. Projektuje architekturę skryptów, które są w stanie wessać tysiące rekordów do Odoo, implementując np. stronicowanie po 200 rekordów, dzięki czemu omija limity pamięci i timeouty serwera. Przykład: "Przygotuj skrypt importujący 50 000 produktów z wbudowanym paczkowaniem."',
        },
        "FINANCIAL_AUDIT": {
            "icon": "💰",
            "name": "Financial Audit",
            "desc": "Lock Dates, Credit Note",
            "tooltip": 'Strażnik ksiąg rachunkowych. Ekspert od mechanizmów modułu księgowości Odoo. Pilnuje bezpieczeństwa operacji finansowych, zarządzania notami kredytowymi i bezwzględnie egzekwuje prawidłowe korzystanie z dat blokady (Lock Dates). Przykład: "Zweryfikuj czy zeszłomiesięczny bilans nie został naruszony przez Lock Dates."',
        },
        "SECURITY_AUDIT": {
            "icon": "🔒",
            "name": "Security Audit",
            "desc": "PII Pseudonymization",
            "tooltip": 'Tarczownik systemu i danych osobowych. Identyfikuje luki zabezpieczeń (np. niewłaściwe Record Rules w Odoo) i specjalizuje się w RODO — w tym mechanizmach szyfrowania, anonimizacji oraz pseudonimizacji wrażliwych danych PII. Przykład: "Zweryfikuj Record Rules dla hr.employee, aby pracownicy widzieli tylko swoje paski płacowe."',
        },
        "ODOO_API_EXPERT": {
            "icon": "🔌",
            "name": "API Expert",
            "desc": "API Keys, no auth=public",
            "tooltip": 'Inżynier połączeń zewnętrznych. Buduje i diagnozuje interfejsy wymiany danych (XML-RPC/JSON-RPC/REST). Czuwa nad bezpiecznym uwierzytelnianiem przy pomocy API Keys, bezlitośnie tępiąc niebezpieczne obejścia typu `auth=public`. Przykład: "Skonfiguruj bezpieczne połączenie przez XML-RPC z zewnętrznym systemem WMS."',
        },
        "MAGIC_FIX": {
            "icon": "🪄",
            "name": "Magic Fix",
            "desc": "Force unlock, kryzysowe",
            "tooltip": 'Agent zadań ratunkowych typu "wszystko płonie". Posiada zaawansowane skrypty do siłowego odblokowywania zawieszonych locków w bazie (`force unlock`), uwalniania zablokowanych zadań cron i natychmiastowego przywracania środowisk do działania. Przykład: "Odblokuj wiszące zadanie crona, które od 2 godzin blokuje inne procesy."',
        },
    }

    for skill_name, config in SKILL_REGISTRY.items():
        defaults = ui_defaults.get(
            skill_name.value,
            {
                "icon": "🛠️",
                "name": skill_name.value,
                "desc": "Brak opisu",
                "tooltip": "Brak dodatkowego opisu dla tego skilla.",
            },
        )
        skills.append(
            {
                "id": skill_name.value,
                "icon": defaults["icon"],
                "name": defaults["name"],
                "desc": defaults["desc"],
                "tooltip": defaults.get("tooltip", defaults["desc"]),
                "read_only": config.read_only,
                "shadow": config.requires_shadow_mode,
                "human_override": config.requires_human_override,
            }
        )
    return skills


@router.post("/api/chat", response_model=ChatResponse)
async def handle_chat(
    req: ChatRequest,
    auth_data: Tuple[bytes, str, str] = Depends(require_auth),
    db: Session = Depends(get_db),
):
    import asyncio
    import uuid
    from smartmyodoo.core.chat_repository import ChatRepository
    from smartmyodoo.swarm.llm_client import OpenRouterClient
    from smartmyodoo.swarm.executor import SkillExecutor, RedFlagViolation
    from smartmyodoo.swarm.sandbox import SandboxManager
    from smartmyodoo.swarm.skills.registry import SKILL_REGISTRY
    from smartmyodoo.swarm.models import SkillName
    from smartmyodoo.swarm.skills.skill_config import SkillConfig

    # ── 1. Dispatch intent ──
    if req.selected_skills:
        category_value = "H"
        persona_value = "H"
        recommended_model = "claude-3-opus-20240229"
        selected_skills_to_use = req.selected_skills
    else:
        dispatch_result = dispatcher.classify_intent(req.message)
        category_value = dispatch_result.category.value
        persona_value = (
            dispatch_result.persona.value if dispatch_result.persona else "H"
        )
        recommended_model = dispatch_result.recommended_model
        selected_skills_to_use = (
            [dispatch_result.skill_name.value] if dispatch_result.skill_name else []
        )

    # ── 2. Resolve OpenRouter key (Vault → ENV fallback) ──
    vk, _, _ = auth_data
    openrouter_key = None
    try:
        vault_data = vault.load_vault(vk)
        secret = vault_data.get("OPENROUTER_KEY", {})
        openrouter_key = (
            secret.get("api_key") or secret.get("password") or secret.get("key")
        )
    except Exception:
        pass
    if not openrouter_key:
        openrouter_key = os.environ.get("OPENROUTER_KEY")

    # ── 3. Build executor ──
    chat_repo = ChatRepository(db=db)
    llm = (
        OpenRouterClient(
            api_key=openrouter_key, model=recommended_model, governor=_token_governor
        )
        if openrouter_key
        else None
    )
    sandbox = SandboxManager()

    executor = SkillExecutor(
        llm_client=llm,
        chat_repo=chat_repo,
        workspace_id=req.workspace_id,
        session_id=req.session_id,
        sandbox=sandbox,
        pii=_get_pii(),
    )

    # ── 4. Resolve skill config ──
    skill_config = None
    if selected_skills_to_use:
        skill_key = selected_skills_to_use[0]
        for key, cfg in SKILL_REGISTRY.items():
            if key.value == skill_key:
                skill_config = cfg
                break

    if not skill_config:
        skill_config = SkillConfig(
            name=SkillName.ODOO_BUSINESS_ANALYST,
            system_prompt="Jesteś asystentem SmartMyOdoo. Odpowiadaj krótko i merytorycznie.",
            allowed_tools=["search_knowledge_base"],
            red_flags=[],
            recommended_model=recommended_model,
        )

    # ── 5. Execute (async-safe) ──
    if llm:
        from smartmyodoo.core.models import AuditLog

        try:
            exec_result = await asyncio.to_thread(
                executor.execute, skill_config, req.message
            )
            reply_text = exec_result.get("response", "Brak odpowiedzi od agenta.")

            audit = AuditLog(
                workspace_id=req.workspace_id,
                action="chat_llm",
                details=f"skill={selected_skills_to_use}",
            )
            db.add(audit)
            db.commit()
        except RedFlagViolation:
            reply_text = "⛔ Zablokowano: wykryto niedozwoloną operację."
        except Exception as e:
            reply_text = f"Błąd agenta: {type(e).__name__}"
    else:
        # Fallback — brak klucza LLM
        executor._save_chat("user", req.message)

        PERSONA_REPLIES = {
            "A": "[💻 Developer] Brak klucza OPENROUTER_KEY.",
            "B": "[🗄️ DBA] Brak klucza OPENROUTER_KEY.",
            "C": "[🧪 QA] Brak klucza OPENROUTER_KEY.",
            "D": "[📝 Docs] Brak klucza OPENROUTER_KEY.",
            "E": "[🔍 Scout] Brak klucza OPENROUTER_KEY.",
            "F": "[🏗️ Architect] Brak klucza OPENROUTER_KEY.",
            "G": "[📊 PM] Brak klucza OPENROUTER_KEY.",
            "H": "[🤖 Asystent] Brak klucza OPENROUTER_KEY w Vault lub ENV.",
        }
        reply_prefix = PERSONA_REPLIES.get(category_value, PERSONA_REPLIES["H"])
        reply_text = reply_prefix + " " + req.message
        executor._save_chat("assistant", reply_text)

    # ── 6. Shadow proposal (only for DBA intent without LLM) ──
    if category_value == "B" and not llm:
        proposal_id = str(uuid.uuid4())[:8]
        from smartmyodoo.core.models import Proposal

        proposal = Proposal(
            id=proposal_id,
            workspace_id=req.workspace_id,
            odoo_model="res.partner",
            method="CREATE",
            values=json.dumps({"name": "Z wiadomości: " + req.message[:50]}),
            reason=f"Dispatcher wykrył intencję bazodanową: {req.message[:80]}",
            status="pending",
        )
        db.add(proposal)
        db.commit()

        return ChatResponse(
            reply=reply_text,
            action_type="SHADOW_PROPOSAL",
            category=category_value,
            persona=persona_value,
            model=recommended_model,
            selected_skills=selected_skills_to_use,
            proposal_data=ChatProposalData(
                proposal_id=proposal_id,
                text=str(proposal.reason),
                model=str(proposal.odoo_model),
                method=str(proposal.method),
                args=[json.loads(str(proposal.values))],
            ),
        )

    return ChatResponse(
        reply=reply_text,
        action_type="CHAT",
        category=category_value,
        persona=persona_value,
        model=recommended_model,
        selected_skills=selected_skills_to_use,
    )


@router.post("/api/pipeline/run")
async def run_pipeline(
    req: PipelineRunRequest,
    auth_data: Tuple[bytes, str, str] = Depends(require_auth),
    db: Session = Depends(get_db),
):
    import asyncio
    import uuid
    from smartmyodoo.core.chat_repository import ChatRepository
    from smartmyodoo.swarm.llm_client import OpenRouterClient
    from smartmyodoo.swarm.executor import SkillExecutor
    from smartmyodoo.swarm.sandbox import SandboxManager
    from smartmyodoo.swarm.pipeline import ExecutionPipeline
    from smartmyodoo.swarm.db_manager import OdooDBManager
    from smartmyodoo.swarm.adp import DecisionEngine
    from smartmyodoo.swarm.recon import EnvironmentRecon

    vk, role, pwd = auth_data

    chat_repo = ChatRepository(db=db)

    # -- Resolve secrets from Vault (SEC-01/SEC-02) --
    vault_data = {}
    openrouter_key = None
    odoo_url = os.environ.get("ODOO_URL", "http://localhost:8069")
    odoo_master_pwd = os.environ.get("ODOO_MASTER_PASSWORD", "")
    odoo_db_name = os.environ.get("ODOO_DB", "odoo_prod")
    try:
        vault_data = vault.load_vault(vk)
        secret = vault_data.get("OPENROUTER_KEY", {})
        openrouter_key = (
            secret.get("api_key") or secret.get("password") or secret.get("key")
        )
        # Odoo connection from Vault
        odoo_secret = vault_data.get("ODOO", vault_data.get("ODOO_URL", {}))
        if isinstance(odoo_secret, dict):
            odoo_url = odoo_secret.get("url", odoo_url)
        master_secret = vault_data.get("ODOO_MASTER_PASSWORD", {})
        if isinstance(master_secret, dict):
            odoo_master_pwd = master_secret.get("password", odoo_master_pwd)
        db_secret = vault_data.get("ODOO_DB", {})
        if isinstance(db_secret, dict):
            odoo_db_name = db_secret.get("password", db_secret.get("db", odoo_db_name))
        elif isinstance(db_secret, str):
            odoo_db_name = db_secret
    except Exception:
        pass
    if not openrouter_key:
        openrouter_key = os.environ.get("OPENROUTER_KEY")

    llm = (
        OpenRouterClient(api_key=openrouter_key, governor=_token_governor)
        if openrouter_key
        else None
    )
    sandbox = SandboxManager(odoo_url=odoo_url, master_password=odoo_master_pwd)
    session_id = req.session_id or str(uuid.uuid4())

    executor = SkillExecutor(
        llm_client=llm,
        chat_repo=chat_repo,
        workspace_id=req.workspace_id,
        session_id=session_id,
        sandbox=sandbox,
        pii=_get_pii(),
    )

    db_manager = OdooDBManager(odoo_url, odoo_master_pwd)
    decision_engine = DecisionEngine(llm_client=llm)
    recon_engine = EnvironmentRecon(db_manager)

    pipeline = ExecutionPipeline(
        db_manager=db_manager,
        decision_engine=decision_engine,
        recon_engine=recon_engine,
        executor=executor,
        db_session=db,
        workspace_id=req.workspace_id,
    )

    # BUG-01: Run pipeline in background thread to avoid blocking
    await asyncio.to_thread(pipeline.run, req.message, "H", odoo_db_name, pwd)

    # BUG-03: Distinguish success from rollback
    return {
        "success": not pipeline._rolled_back,
        "final_state": pipeline.state.name,
        "adp_plan": pipeline.adp_plan,
        "rolled_back": pipeline._rolled_back,
    }


@router.websocket("/api/chat/stream")
async def chat_stream_endpoint(websocket: WebSocket, db: Session = Depends(get_db)):
    """
    Strumieniuje odpowiedź modelu używając WebSockets.
    Klient najpierw wysyła JSON: {message, workspace_id, session_id, password, selected_skills}
    Server odpowiada strumieniem chunków: {"type": "token"|"log"|"error"|"done", "content": ...}
    """
    await websocket.accept()

    import uuid
    import asyncio
    import logging
    from smartmyodoo.core.chat_repository import ChatRepository
    from smartmyodoo.swarm.llm_client import OpenRouterClient
    from smartmyodoo.swarm.executor import SkillExecutor
    from smartmyodoo.swarm.sandbox import SandboxManager
    from smartmyodoo.swarm.skills.registry import SKILL_REGISTRY
    from smartmyodoo.swarm.models import SkillName
    from smartmyodoo.swarm.skills.skill_config import SkillConfig

    logger = logging.getLogger(__name__)

    try:
        data = await websocket.receive_text()
        req_data = json.loads(data)

        message = req_data.get("message", "")
        workspace_id = req_data.get("workspace_id", "default")
        session_id = req_data.get("session_id", str(uuid.uuid4()))
        pwd = req_data.get("password", "")
        selected_skills = req_data.get("selected_skills", [])

        # 1. Auth manual (ponieważ WebSocket i headers bywają problematyczne w niektórych klientach)
        vk, role = get_auth_key(pwd)
        if not vk:
            await websocket.send_json(
                {"type": "error", "content": "Invalid credentials"}
            )
            await websocket.close(code=1008)
            return

        # 2. Dispatch
        if selected_skills:
            recommended_model = "claude-3-opus-20240229"
            selected_skills_to_use = selected_skills
        else:
            dispatch_result = dispatcher.classify_intent(message)
            recommended_model = dispatch_result.recommended_model
            selected_skills_to_use = (
                [dispatch_result.skill_name.value] if dispatch_result.skill_name else []
            )

        # 3. LLM Key
        openrouter_key = None
        try:
            vault_data = vault.load_vault(vk)
            secret = vault_data.get("OPENROUTER_KEY", {})
            openrouter_key = (
                secret.get("api_key") or secret.get("password") or secret.get("key")
            )
        except Exception:
            pass
        if not openrouter_key:
            openrouter_key = os.environ.get("OPENROUTER_KEY")

        if not openrouter_key:
            await websocket.send_json(
                {
                    "type": "error",
                    "content": "Brak klucza OPENROUTER_KEY w Vault lub ENV.",
                }
            )
            await websocket.close(code=1000)
            return

        # 4. Executor
        chat_repo = ChatRepository(db=db)
        llm = OpenRouterClient(
            api_key=openrouter_key, model=recommended_model, governor=_token_governor
        )
        sandbox = SandboxManager()

        executor = SkillExecutor(
            llm_client=llm,
            chat_repo=chat_repo,
            workspace_id=workspace_id,
            session_id=session_id,
            sandbox=sandbox,
            pii=_get_pii(),
        )

        skill_config = None
        if selected_skills_to_use:
            skill_key = selected_skills_to_use[0]
            for key, cfg in SKILL_REGISTRY.items():
                if key.value == skill_key:
                    skill_config = cfg
                    break

        if not skill_config:
            skill_config = SkillConfig(
                name=SkillName.ODOO_BUSINESS_ANALYST,
                system_prompt="Jesteś asystentem SmartMyOdoo.",
                allowed_tools=[],
                red_flags=[],
                recommended_model=recommended_model,
            )

        # Audit
        from smartmyodoo.core.models import AuditLog

        audit = AuditLog(
            workspace_id=workspace_id,
            action="chat_ws_stream",
            details=f"skill={selected_skills_to_use}",
        )
        db.add(audit)
        db.commit()

        # 5. Run Generator
        if req_data.get("use_pipeline", False):
            from smartmyodoo.swarm.pipeline import ExecutionPipeline
            from smartmyodoo.swarm.db_manager import OdooDBManager
            from smartmyodoo.swarm.adp import DecisionEngine
            from smartmyodoo.swarm.recon import EnvironmentRecon

            # SEC-01/SEC-02: Read Odoo credentials from Vault
            ws_odoo_url = os.environ.get("ODOO_URL", "http://localhost:8069")
            ws_odoo_master_pwd = os.environ.get("ODOO_MASTER_PASSWORD", "")
            ws_odoo_db_name = os.environ.get("ODOO_DB", "odoo_prod")
            try:
                ws_vault_data = vault.load_vault(vk)
                ws_odoo_secret = ws_vault_data.get(
                    "ODOO", ws_vault_data.get("ODOO_URL", {})
                )
                if isinstance(ws_odoo_secret, dict):
                    ws_odoo_url = ws_odoo_secret.get("url", ws_odoo_url)
                ws_master_secret = ws_vault_data.get("ODOO_MASTER_PASSWORD", {})
                if isinstance(ws_master_secret, dict):
                    ws_odoo_master_pwd = ws_master_secret.get(
                        "password", ws_odoo_master_pwd
                    )
                ws_db_secret = ws_vault_data.get("ODOO_DB", {})
                if isinstance(ws_db_secret, dict):
                    ws_odoo_db_name = ws_db_secret.get(
                        "password", ws_db_secret.get("db", ws_odoo_db_name)
                    )
                elif isinstance(ws_db_secret, str):
                    ws_odoo_db_name = ws_db_secret
            except Exception:
                pass

            db_manager = OdooDBManager(ws_odoo_url, ws_odoo_master_pwd)
            decision_engine = DecisionEngine(llm_client=llm)
            recon_engine = EnvironmentRecon(db_manager)

            loop = asyncio.get_running_loop()

            def on_transition(phase: str):
                asyncio.run_coroutine_threadsafe(
                    websocket.send_json({"type": "fsm_state", "phase": phase}), loop
                )

            pipeline = ExecutionPipeline(
                db_manager=db_manager,
                decision_engine=decision_engine,
                recon_engine=recon_engine,
                executor=executor,
                db_session=None,  # Set inside thread
                workspace_id=workspace_id,
                on_transition_callback=on_transition,
            )

            def run_pipeline_thread():
                from smartmyodoo.core.database import SessionLocal

                thread_db = SessionLocal()
                try:
                    pipeline.db_session = thread_db
                    pipeline.run(message, "H", ws_odoo_db_name, pwd)
                finally:
                    thread_db.close()

            await asyncio.to_thread(run_pipeline_thread)
            await websocket.send_json(
                {
                    "type": "done",
                    "content": pipeline.adp_plan.get("response", "Zakończono Pipeline"),
                    "rolled_back": pipeline._rolled_back,
                }
            )
        else:
            generator = executor.execute_stream(skill_config, message)
            async for chunk in generator:
                await websocket.send_json(chunk)

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await websocket.send_json({"type": "error", "content": str(e)})
        except Exception:
            pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass
