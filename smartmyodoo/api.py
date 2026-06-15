import os
import datetime
import json
from typing import Dict, Any, Tuple, Optional
from pydantic import BaseModel
from fastapi import (
    FastAPI,
    Depends,
    HTTPException,
    Request,
    Security,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from smartmyodoo.core.database import get_db, engine
from smartmyodoo.core import models as db_models

from smartmyodoo.vault import vault
from smartmyodoo.vault import schemas
from smartmyodoo.swarm.models import (
    ChatRequest,
    ChatResponse,
    ChatProposalData,
)
from smartmyodoo.swarm.dispatcher import Dispatcher
from smartmyodoo.swarm import llm_client
from smartmyodoo.mcp.token_governor import governor as _token_governor
from typing import List


class PipelineRunRequest(BaseModel):
    message: str
    workspace_id: str = "default"
    session_id: str = ""
    selected_skills: List[str] = []
    use_pipeline: bool = True


db_models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="SmartMyVault API", description="FastAPI migration of Vault API")

# S1.3: jawna lista originów (koniec '*'+credentials, które echo'wało dowolny Origin).
# Konfiguracja przez CORS_ALLOWED_ORIGINS (CSV); domyślnie lokalny UI.
_cors_origins = [
    o.strip()
    for o in os.environ.get(
        "CORS_ALLOWED_ORIGINS", "http://127.0.0.1:8000,http://localhost:8000"
    ).split(",")
    if o.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

security = HTTPBearer()

# LLM Client: odczyt klucza z ENV (opcjonalnie wstrzyknięty przez Vault CLI)
_llm = llm_client.create_client(api_key=os.environ.get("OPENROUTER_KEY"))
dispatcher = Dispatcher(llm_client=_llm)

# S1.1: współdzielona instancja PiiMiddleware (mapping per workspace_id), lazy by nie ładować
# presidio przy imporcie modułu.
_pii_singleton = None


def _get_pii():
    global _pii_singleton
    if _pii_singleton is None:
        from smartmyodoo.mcp.pii_middleware import PiiMiddleware

        _pii_singleton = PiiMiddleware()
    return _pii_singleton


# Zastąpiono _proposals i _workspaces użyciem bazy danych.


def get_auth_key(pwd: str) -> Tuple[Optional[bytes], Optional[str]]:
    try:
        vk = vault.get_vault_key_from_master(pwd, exit_on_fail=False)
        return vk, "admin"
    except (vault.InvalidToken, ValueError):
        pass
    try:
        vk = vault.get_vault_key_from_pin(pwd, exit_on_fail=False)
        return vk, "user"
    except (vault.InvalidToken, ValueError):
        return None, None


def require_auth(
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> Tuple[bytes, str, str]:
    pwd = credentials.credentials
    vk, role = get_auth_key(pwd)
    if not vk:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return vk, str(role), pwd


@app.get("/api/status")
async def status():
    is_init = os.path.exists(vault.VAULT_DATA_FILE)
    return {"initialized": is_init}


@app.post("/api/init", response_model=schemas.SuccessResponse)
async def init_api(data: schemas.InitRequest):
    if os.path.exists(vault.VAULT_DATA_FILE):
        raise HTTPException(status_code=400, detail="Already initialized")

    try:
        vault.init_vault_core(data.pin, data.master)
        return schemas.SuccessResponse(success=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class _AuthRateLimiter:
    """S1.3: prosty rate-limit/lockout prób logowania (ochrona przed brute-force PIN)."""

    def __init__(self, max_attempts: int = 5, window_seconds: int = 300):
        self.max_attempts = max_attempts
        self.window = window_seconds
        self._attempts: Dict[str, Dict[str, float]] = {}

    @staticmethod
    def _now() -> float:
        import time

        return time.monotonic()

    def is_locked(self, key: str) -> bool:
        rec = self._attempts.get(key)
        if not rec:
            return False
        if self._now() - rec["first"] >= self.window:
            self._attempts.pop(key, None)
            return False
        return rec["count"] >= self.max_attempts

    def record_failure(self, key: str) -> None:
        now = self._now()
        rec = self._attempts.get(key)
        if not rec or now - rec["first"] >= self.window:
            self._attempts[key] = {"count": 1.0, "first": now}
        else:
            rec["count"] += 1

    def reset(self, key: str) -> None:
        self._attempts.pop(key, None)


_auth_limiter = _AuthRateLimiter()


@app.post("/api/auth", response_model=schemas.AuthResponse)
async def auth(data: schemas.AuthRequest, request: Request):
    client = request.client.host if request.client else "unknown"
    if _auth_limiter.is_locked(client):
        raise HTTPException(
            status_code=429,
            detail="Zbyt wiele nieudanych prób logowania. Spróbuj ponownie później.",
        )
    vk, role = get_auth_key(data.password)
    if vk:
        _auth_limiter.reset(client)
        return schemas.AuthResponse(success=True, role=role)
    _auth_limiter.record_failure(client)
    raise HTTPException(status_code=401, detail="Invalid credentials")


@app.get("/api/secrets", response_model=Dict[str, Any])
async def get_secrets(
    workspace_id: Optional[str] = None,
    auth_data: Tuple[bytes, str, str] = Depends(require_auth),
):
    vk, _, _ = auth_data
    try:
        data = vault.get_secrets(vk)
        if workspace_id:
            filtered_data = {
                k: v
                for k, v in data.items()
                if isinstance(v, dict)
                and v.get("workspace_id", "default") == workspace_id
            }
            return filtered_data
        return data
    except vault.VaultDecryptionError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/secrets/{key_name}", response_model=schemas.SuccessResponse)
async def add_or_update_secret(
    key_name: str,
    secret_data: schemas.SecretCreateRequest,
    auth_data: Tuple[bytes, str, str] = Depends(require_auth),
):
    vk, _, _ = auth_data
    try:
        data = vault.load_vault(vk)
        data[key_name] = {
            "password": secret_data.password,
            "login": secret_data.login,
            "url": secret_data.url,
            "db": secret_data.db,
            "api_key": secret_data.api_key,
            "expires": secret_data.expires,
            "workspace_id": secret_data.workspace_id,
        }
        vault.save_vault(vk, data)
        return schemas.SuccessResponse(success=True)
    except vault.VaultDecryptionError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/secrets/{key_name}", response_model=schemas.SuccessResponse)
async def delete_secret(
    key_name: str, auth_data: Tuple[bytes, str, str] = Depends(require_auth)
):
    vk, _, _ = auth_data
    try:
        data = vault.load_vault(vk)
        if key_name in data:
            data[key_name]["deleted_at"] = datetime.datetime.now().isoformat()
            vault.save_vault(vk, data)
            return schemas.SuccessResponse(success=True)
        raise HTTPException(status_code=404, detail="Not found")
    except vault.VaultDecryptionError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/secrets/{key_name}/restore", response_model=schemas.SuccessResponse)
async def restore_secret(
    key_name: str, auth_data: Tuple[bytes, str, str] = Depends(require_auth)
):
    vk, _, _ = auth_data
    try:
        data = vault.load_vault(vk)
        if (
            key_name in data
            and isinstance(data[key_name], dict)
            and "deleted_at" in data[key_name]
        ):
            del data[key_name]["deleted_at"]
            vault.save_vault(vk, data)
            return schemas.SuccessResponse(success=True)
        raise HTTPException(status_code=404, detail="Not found or not deleted")
    except vault.VaultDecryptionError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/secrets/{key_name}/permanent", response_model=schemas.SuccessResponse)
async def permanent_delete_secret(
    key_name: str, auth_data: Tuple[bytes, str, str] = Depends(require_auth)
):
    vk, _, _ = auth_data
    try:
        data = vault.load_vault(vk)
        if key_name in data:
            del data[key_name]
            vault.save_vault(vk, data)
            return schemas.SuccessResponse(success=True)
        raise HTTPException(status_code=404, detail="Not found")
    except vault.VaultDecryptionError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/change-pin", response_model=schemas.SuccessResponse)
async def change_pin(
    req: schemas.ChangePinRequest,
    auth_data: Tuple[bytes, str, str] = Depends(require_auth),
):
    vk, role, _ = auth_data
    if role != "admin":
        raise HTTPException(status_code=403, detail="Admin role required to change PIN")

    try:
        vault.update_pin(vk, req.new_pin)
        return schemas.SuccessResponse(success=True, message="PIN zaktualizowany")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/skills")
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


@app.post("/api/chat", response_model=ChatResponse)
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


@app.post("/api/pipeline/run")
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


@app.websocket("/api/chat/stream")
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


# ── EP-Agent: Agent Status API ───────────────────────────────────────────────


@app.get("/api/agent/status")
async def get_agent_status(
    auth_data: Tuple[bytes, str, str] = Depends(require_auth),
):
    """Zwraca obecny status działania agenta (mock na potrzeby UI)."""
    return {"status": "idle", "task": None, "step": None, "elapsed_s": 0}


# ── EP-1: Chat Sessions API ──────────────────────────────────────────────────


@app.get("/api/chat/sessions")
async def get_chat_sessions(
    workspace_id: str = "default",
    limit: int = 20,
    auth_data: Tuple[bytes, str, str] = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Lista sesji czatu dla danego workspace (Smart Context)."""
    from smartmyodoo.core.chat_repository import ChatRepository

    repo = ChatRepository(db=db)
    return repo.list_sessions(workspace_id, limit=limit)


@app.get("/api/chat/sessions/{session_id}/messages")
async def get_session_messages(
    session_id: str,
    limit: int = 200,
    auth_data: Tuple[bytes, str, str] = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Pełna historia wiadomości z konkretnej sesji (on-demand load)."""
    from smartmyodoo.core.chat_repository import ChatRepository

    repo = ChatRepository(db=db)
    return repo.get_session_messages(session_id, limit=limit)


# ── EP-3: Audit Trail API ────────────────────────────────────────────────────


@app.get("/api/audit")
async def get_audit_log(
    workspace_id: Optional[str] = None,
    limit: int = 50,
    auth_data: Tuple[bytes, str, str] = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Pobierz ostatnie wpisy z dziennika audytu."""
    query = db.query(db_models.AuditLog).order_by(db_models.AuditLog.timestamp.desc())
    if workspace_id:
        query = query.filter(db_models.AuditLog.workspace_id == workspace_id)
    entries = query.limit(limit).all()
    return [
        {
            "id": e.id,
            "workspace_id": e.workspace_id,
            "timestamp": e.timestamp.isoformat() if e.timestamp else "",
            "action": e.action,
            "details": e.details,
        }
        for e in entries
    ]


# ── HUB-S3: Proposals API → wydzielone do api_routers/proposals.py (S3.1) ──


# ── HUB-S3: Workspaces API ──────────────────────────────────────────────────────────────


@app.get("/api/workspaces")
async def get_workspaces(
    auth_data: Tuple[bytes, str, str] = Depends(require_auth),
    db: Session = Depends(get_db),
):
    wks = db.query(db_models.Workspace).order_by(db_models.Workspace.position).all()
    if not wks:
        # Defaults if empty
        default_wks = [
            db_models.Workspace(id="default", name="Domyślna", position=0),
            db_models.Workspace(id="dev", name="Dev Env", position=1),
            db_models.Workspace(id="prod", name="Production", position=2),
        ]
        db.add_all(default_wks)
        db.commit()
        wks = db.query(db_models.Workspace).order_by(db_models.Workspace.position).all()

    return [
        {
            "id": w.id,
            "name": w.name,
            "odoo_url": w.odoo_url,
            "position": w.position,
            "project_ref": w.project_ref,
            "project_name": w.project_name,
            "task_ref": w.task_ref,
            "task_name": w.task_name,
        }
        for w in wks
    ]


# ── EP-5.4: Project + Task Binding API ───────────────────────────────────────


def _get_odoo_connector(vk, ws_id):
    """Helper: pobiera OdooProjectConnector z poświadczeń Vault dla danego workspace."""
    vault_data = vault.load_vault(vk)
    secret_key = f"{ws_id}_ODOO"
    if secret_key not in vault_data:
        secret_key = "default_ODOO"  # nosec B105
    if secret_key not in vault_data:
        raise HTTPException(
            status_code=400, detail="Brak poświadczeń Odoo w sejfie dla tego workspace."
        )
    creds = vault_data[secret_key]
    from smartmyodoo.core.odoo_connector import OdooProjectConnector

    return OdooProjectConnector(creds)


@app.get("/api/workspaces/{ws_id}/projects/search")
async def search_odoo_projects(
    ws_id: str,
    query: str = "",
    auth_data: Tuple[bytes, str, str] = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Szuka projektów w Odoo (project.project)."""
    vk, _, _ = auth_data
    try:
        connector = _get_odoo_connector(vk, ws_id)
        domain = [("name", "ilike", query)] if query else []
        projects = connector.execute_kw(
            model="project.project",
            method="search_read",
            args=[domain],
            kw={"fields": ["id", "name"], "limit": 30},
        )
        return projects
    except vault.VaultDecryptionError:
        raise HTTPException(status_code=500, detail="Błąd deszyfrowania sejfu")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/workspaces/{ws_id}/projects/{project_id}/tasks")
async def list_project_tasks(
    ws_id: str,
    project_id: int,
    auth_data: Tuple[bytes, str, str] = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Zwraca wszystkie zadania z danego projektu Odoo."""
    vk, _, _ = auth_data
    try:
        connector = _get_odoo_connector(vk, ws_id)
        domain = [("project_id", "=", project_id)]
        tasks = connector.execute_kw(
            model="project.task",
            method="search_read",
            args=[domain],
            kw={"fields": ["id", "name", "stage_id", "user_ids"], "limit": 200},
        )
        return tasks
    except vault.VaultDecryptionError:
        raise HTTPException(status_code=500, detail="Błąd deszyfrowania sejfu")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/workspaces/{ws_id}/tasks/search")
async def search_odoo_tasks(
    ws_id: str,
    query: str = "",
    auth_data: Tuple[bytes, str, str] = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Szuka zadań w Odoo (project.task) — zachowane dla kompatybilności."""
    vk, _, _ = auth_data
    try:
        connector = _get_odoo_connector(vk, ws_id)
        domain = [("name", "ilike", query)] if query else []
        tasks = connector.execute_kw(
            model="project.task",
            method="search_read",
            args=[domain],
            kw={"fields": ["id", "name", "project_id"], "limit": 20},
        )
        return tasks
    except vault.VaultDecryptionError:
        raise HTTPException(status_code=500, detail="Błąd deszyfrowania sejfu")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class TimesheetRequest(BaseModel):
    hours: float
    description: str
    task_id: Optional[int] = None
    is_nominal: bool = False


@app.post("/api/workspaces/{ws_id}/timesheet")
async def log_timesheet(
    ws_id: str,
    payload: TimesheetRequest,
    auth_data: Tuple[bytes, str, str] = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Zapisuje wpis czasu pracy (timesheet) do Odoo."""
    ws = db.query(db_models.Workspace).filter(db_models.Workspace.id == ws_id).first()
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")

    vk, _, _ = auth_data
    try:
        connector = _get_odoo_connector(vk, ws_id)

        task_id = payload.task_id
        is_nominal = payload.is_nominal

        if not is_nominal and not task_id:
            task_id = int(ws.task_ref) if ws.task_ref else None

            if not task_id and ws.project_ref:
                try:
                    task_id = connector.create_task(
                        int(ws.project_ref), "[SmartMyOdoo] Pula czasu roboczego"
                    )
                    ws.task_ref = str(task_id)  # type: ignore
                    ws.task_name = "[SmartMyOdoo] Pula czasu roboczego"  # type: ignore
                    db.commit()
                except Exception as e:
                    raise HTTPException(
                        status_code=500, detail=f"Błąd auto-create task: {str(e)}"
                    )

        if not task_id:
            raise HTTPException(
                status_code=400, detail="Brak ID zadania (task_id) dla logowania czasu."
            )

        project_id = ws.project_ref
        if not project_id:
            raise HTTPException(status_code=400, detail="Najpierw wybierz projekt.")

        entry_id = connector.log_timesheet(
            project_id=int(project_id),
            task_id=int(task_id),
            hours=payload.hours,
            description=payload.description,
        )
        return {"success": True, "timesheet_id": entry_id}
    except vault.VaultDecryptionError:
        raise HTTPException(status_code=500, detail="Błąd deszyfrowania sejfu")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class TaskBindRequest(BaseModel):
    project_ref: str
    project_name: str
    task_ref: str = ""
    task_name: str = ""


@app.put("/api/workspaces/{ws_id}/task_bind")
async def bind_workspace_task(
    ws_id: str,
    payload: TaskBindRequest,
    auth_data: Tuple[bytes, str, str] = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Zapisuje powiązanie projektu + domyślnego zadania."""
    ws = db.query(db_models.Workspace).filter(db_models.Workspace.id == ws_id).first()
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")

    ws.project_ref = payload.project_ref  # type: ignore
    ws.project_name = payload.project_name  # type: ignore
    ws.task_ref = payload.task_ref  # type: ignore
    ws.task_name = payload.task_name  # type: ignore
    db.commit()
    return {
        "success": True,
        "project_ref": ws.project_ref,
        "project_name": ws.project_name,
        "task_ref": ws.task_ref,
        "task_name": ws.task_name,
    }


@app.post("/api/workspaces")
async def create_workspace(
    ws: schemas.WorkspaceCreateRequest,
    auth_data: Tuple[bytes, str, str] = Depends(require_auth),
    db: Session = Depends(get_db),
):
    existing = (
        db.query(db_models.Workspace).filter(db_models.Workspace.id == ws.id).first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="Workspace ID already exists")
    max_pos = db.query(db_models.Workspace).count()
    new_ws = db_models.Workspace(
        id=ws.id, name=ws.name, odoo_url=ws.odoo_url, position=max_pos
    )
    db.add(new_ws)
    db.commit()

    vault_saved = False
    if ws.admin_password:
        vk, _, _ = auth_data
        try:
            vault_data = vault.load_vault(vk)
            secret_key = f"{ws.id}_ODOO"
            vault_data[secret_key] = {
                "password": ws.admin_password,
                "login": ws.admin_login or "",
                "api_key": ws.admin_api_key or "",
                "url": ws.odoo_url or "",
                "workspace_id": ws.id,
                "expires": ws.admin_expires or "",
            }
            vault.save_vault(vk, vault_data)
            vault_saved = True
        except vault.VaultDecryptionError as e:
            import logging

            logging.warning(f"Vault write failed for workspace {ws.id}: {e}")

    return {"success": True, "id": ws.id, "vault_saved": vault_saved}


@app.put("/api/workspaces/reorder")
async def reorder_workspaces(
    body: dict,
    auth_data: Tuple[bytes, str, str] = Depends(require_auth),
    db: Session = Depends(get_db),
):
    order = body.get("order", [])
    if not order:
        raise HTTPException(status_code=400, detail="Empty order list")

    for idx, ws_id in enumerate(order):
        ws = (
            db.query(db_models.Workspace)
            .filter(db_models.Workspace.id == ws_id)
            .first()
        )
        if ws:
            ws.position = idx  # type: ignore
    db.commit()
    return {"success": True}


@app.put("/api/workspaces/{ws_id}")
async def update_workspace(
    ws_id: str,
    update_data: dict,
    auth_data: Tuple[bytes, str, str] = Depends(require_auth),
    db: Session = Depends(get_db),
):
    ws = db.query(db_models.Workspace).filter(db_models.Workspace.id == ws_id).first()
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")

    ws.name = update_data.get("name", ws.name)
    ws.odoo_url = update_data.get("odoo_url", ws.odoo_url)
    db.commit()
    return {"success": True}


@app.delete("/api/workspaces/{ws_id}")
async def delete_workspace(
    ws_id: str,
    cascade_vault: bool = False,
    auth_data: Tuple[bytes, str, str] = Depends(require_auth),
    db: Session = Depends(get_db),
):
    ws = db.query(db_models.Workspace).filter(db_models.Workspace.id == ws_id).first()
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")

    secrets_removed = 0
    if cascade_vault:
        vk, _, _ = auth_data
        try:
            vault_data = vault.load_vault(vk)
            for key, val in list(vault_data.items()):
                if isinstance(val, dict) and val.get("workspace_id") == ws_id:
                    vault_data[key]["deleted_at"] = datetime.datetime.now().isoformat()
                    secrets_removed += 1
            if secrets_removed > 0:
                vault.save_vault(vk, vault_data)
        except vault.VaultDecryptionError as e:
            import logging

            logging.warning(f"Vault cascade failed for workspace {ws_id}: {e}")

    db.delete(ws)
    db.commit()
    return {"success": True, "secrets_removed": secrets_removed}


@app.delete("/api/secrets/by-workspace/{ws_id}")
async def delete_secrets_by_workspace(
    ws_id: str,
    auth_data: Tuple[bytes, str, str] = Depends(require_auth),
):
    vk, _, _ = auth_data
    try:
        vault_data = vault.load_vault(vk)
        removed = 0
        for key, val in list(vault_data.items()):
            if isinstance(val, dict) and val.get("workspace_id") == ws_id:
                vault_data[key]["deleted_at"] = datetime.datetime.now().isoformat()
                removed += 1
        if removed > 0:
            vault.save_vault(vk, vault_data)
        return {"success": True, "secrets_removed": removed}
    except vault.VaultDecryptionError as e:
        raise HTTPException(status_code=500, detail=str(e))


# S3.1: routery domenowe wydzielone z God Module (przed catch-all mount /).
# Late import — require_auth jest już zdefiniowane wyżej (brak cyklu).
from smartmyodoo.api_routers.proposals import router as proposals_router  # noqa: E402

app.include_router(proposals_router)

ui_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ui")
app.mount("/", StaticFiles(directory=ui_dir, html=True), name="ui")


def start_server(port=8000):
    import uvicorn
    import webbrowser
    import threading
    import time

    url = f"http://127.0.0.1:{port}"
    print("==================================================")
    print(f"|  FastAPI Vault Server działa: {url} |")
    print("|  Proszę nie zamykać tej konsoli.               |")
    print("==================================================")

    def open_browser():
        time.sleep(1)
        webbrowser.open(url + "/")

    threading.Thread(target=open_browser, daemon=True).start()

    uvicorn.run("smartmyodoo.api:app", host="127.0.0.1", port=port, log_level="info")


if __name__ == "__main__":
    start_server()
