"""FIX-02 S3.1b: domena `chat` wydzielona z God Module api.py.

Endpointy: GET /api/skills, POST /api/chat, POST /api/pipeline/run, WS /api/chat/stream.
Zależności (dispatcher, PII) z `chat_deps` — NIE z api.py (zero cyklu, patrz S3.4).
governor bezpośrednio z mcp.token_governor; auth z api_deps. Zachowanie bez zmian.
"""

import os
import json
from typing import List, Tuple

from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from smartmyodoo.core.database import get_db
from smartmyodoo.core.ratelimit import chat_limiter
from smartmyodoo.core.odoo_connector import sanitize_db_name
from smartmyodoo.mcp.odoo_client import (
    set_odoo_creds,
    set_odoo_unconfigured,
    OdooWorkspaceUnconfigured,
)
from smartmyodoo.mcp.odoo_errors import classify_odoo_error
from smartmyodoo.vault import vault
from smartmyodoo.vault.resolver import resolve_llm_key, resolve_credential
from smartmyodoo.vault.schemas import CredentialType
from smartmyodoo.swarm.models import ChatRequest, ChatResponse, ChatProposalData
from smartmyodoo.swarm.model_policy import effective_model, MODEL_POLICY, ModelTier
from smartmyodoo.mcp.token_governor import governor as _token_governor
from smartmyodoo.api_deps import require_auth, get_auth_key
from smartmyodoo.chat_deps import (
    dispatcher,
    get_pii as _get_pii,
    get_llm_cache,
    get_conversation_scope as _get_scope,
)

router = APIRouter(tags=["chat"])


def _enforce_chat_rate(workspace_id: str) -> None:
    """FIX-03: throttling per workspace — 429 gdy przekroczono limit żądań/okno."""
    if not chat_limiter.allow(f"chat:{workspace_id or 'default'}"):
        raise HTTPException(
            status_code=429,
            detail="Zbyt wiele żądań — spróbuj ponownie za chwilę.",
            headers={"Retry-After": str(chat_limiter.retry_after)},
        )


def _inject_odoo_creds(vault_data: dict, workspace_id: str) -> None:
    """KEY-02-3 (ADR-007): wstrzyknij poświadczenia Odoo ze Skarbca (per workspace) do
    kontekstu żądania, aby narzędzia agenta (odoo_search/schema) łączyły się BEZ ENV/`vault run`.

    WSISO-01 (V1+V3): `allow_default_fallback=False` — wybrany nie-`default` workspace
    NIE dziedziczy Odoo z `default`. Przy braku własnego ODOO_DATA ustawiamy marker
    „nieskonfigurowany" → narzędzia Odoo zwrócą jawny błąd zamiast łączyć z cudzą
    instancją/ENV (cross-client). `default` bez creds zachowuje ENV (`vault run`)."""
    cred = resolve_credential(
        vault_data,
        CredentialType.ODOO_DATA,
        workspace_id,
        allow_default_fallback=False,  # WSISO-01 V1: nie-default nie dziedziczy default
    )
    if cred and cred.url and cred.db:
        creds = {
            "url": cred.url,
            "db": sanitize_db_name(cred.db),
            "username": cred.login or "",
            "password": cred.api_key or cred.password or "",
        }
        # KEY-02-3: zapisz pod realnym workspace ORAZ pod "default". Narzędzia (odoo_search/
        # schema/create) NIE przekazują workspace_id z LLM → trafiają na OdooClient("default").
        # Kontekst jest per-żądanie (jeden workspace), więc "default" == ten workspace. Bez tego
        # creds wstrzyknięte pod np. "myodooTest" nie byłyby widoczne dla wywołań "default".
        set_odoo_creds({workspace_id: creds, "default": creds})
        set_odoo_unconfigured(None)  # creds OK → wyczyść ewentualny marker
        return
    # WSISO-01 V3 (D3): brak własnych creds Odoo dla tej tury.
    if workspace_id and workspace_id != "default":
        # Wybrany KONKRETNY workspace bez ODOO_DATA → FAIL LOUD (marker). Zero fallbacku
        # do ENV / instancji innego workspace. Czyścimy też creds (świeżość kontekstu).
        set_odoo_creds(None)
        set_odoo_unconfigured(workspace_id)
    else:
        # ws=`default` bez creds → zachowaj ENV/`vault run` (bez markera).
        set_odoo_unconfigured(None)


def _resolve_write_odoo_target(
    vault_data: dict, workspace_id: str, default_url: str, default_db: str
) -> Tuple[str, str]:
    """WSISO-02 (guard tymczasowy): izolacja klienta na ŚCIEŻCE ZAPISU (pipeline/sandbox).

    Pipeline/sandbox budują połączenie z ENV/generycznego sekretu `ODOO` — BEZ rozróżnienia
    workspace (cross-client na ZAPISIE; gorszy wariant WSISO-01, świadomie poza jego D5).
    Guard: wybrany nie-`default` workspace MUSI mieć własny ODOO_DATA — kierujemy połączenie
    na JEGO instancję (url/db); przy braku → `OdooWorkspaceUnconfigured` (głośno) ZAMIAST
    cichego ENV/generic. `default` → ENV/generyczny sekret bez zmian (regres zachowany).

    Uwaga: master-password/semantyka sandboxa NADAL z ENV — pełna izolacja write-path
    (per-ws master-password) to zakres sprintu WSISO-02 (/arch). Guard tylko zamyka
    cichy cross-client leak: nie-default nigdy po cichu nie pisze do bazy ENV/`default`.
    """
    if not workspace_id or workspace_id == "default":
        return default_url, default_db
    cred = resolve_credential(
        vault_data,
        CredentialType.ODOO_DATA,
        workspace_id,
        allow_default_fallback=False,  # WSISO-01 V1: nie-default nie dziedziczy default
    )
    if not (cred and cred.url and cred.db):
        raise OdooWorkspaceUnconfigured(workspace_id)
    return cred.url, sanitize_db_name(cred.db)


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

    # FIX-03: rate-limit per workspace (429 przy zalaniu)
    _enforce_chat_rate(req.workspace_id)

    # ── SELFDOC-01: wiarygodny self-opis ZANIM ruszymy LLM ──
    # „co potrafisz / opowiedz o sobie" → opis z PRAWDZIWEGO rejestru (zero
    # improwizacji/konfabulacji LLM). Pomijamy, gdy user jawnie wybrał skill.
    from smartmyodoo.swarm.capabilities import (
        is_self_describe_query,
        build_capabilities,
    )

    if not req.selected_skills and is_self_describe_query(req.message):
        reply_text = build_capabilities()
        try:
            from smartmyodoo.core.chat_repository import ChatRepository

            repo = ChatRepository(db=db)
            repo.save_message(req.workspace_id, req.session_id, "user", req.message)
            repo.save_message(
                req.workspace_id,
                req.session_id,
                "assistant",
                reply_text,
                {"category": "SELF_DESCRIBE"},
            )
        except Exception:  # noqa: BLE001 — zapis historii to ulepszenie, nie bloker
            pass
        return ChatResponse(
            reply=reply_text,
            action_type="CHAT",
            category="SELF_DESCRIBE",
            persona="H",
            model=None,
            selected_skills=[],
        )

    # ── 1. Dispatch intent ──
    if req.selected_skills:
        category_value = "H"
        persona_value = "H"
        selected_skills_to_use = req.selected_skills
    else:
        dispatch_result = dispatcher.classify_intent(req.message)
        category_value = dispatch_result.category.value
        persona_value = (
            dispatch_result.persona.value if dispatch_result.persona else "H"
        )
        selected_skills_to_use = (
            [dispatch_result.skill_name.value] if dispatch_result.skill_name else []
        )

    # FIX-03: model wg polityki tierów + degradacja przy niskim budżecie (K4/K5)
    _skill_for_model = selected_skills_to_use[0] if selected_skills_to_use else None
    recommended_model = effective_model(_skill_for_model, governor=_token_governor)

    # ── 2. Resolve OpenRouter key (KEY-02: resolver typowany → ENV; ADR-007) ──
    vk, _, _ = auth_data
    try:
        vault_data = vault.load_vault(vk)
    except Exception:
        vault_data = {}
    openrouter_key = resolve_llm_key(vault_data, req.workspace_id)
    _inject_odoo_creds(vault_data, req.workspace_id)  # KEY-02-3: Odoo ze Skarbca

    # ── 3. Build executor ──
    chat_repo = ChatRepository(db=db)
    llm = (
        OpenRouterClient(
            api_key=openrouter_key,
            model=recommended_model,
            governor=_token_governor,
            # FIX: gdy tier (np. PREMIUM) padnie/404 — degraduj do STANDARD zamiast błędu
            fallback_model=MODEL_POLICY[ModelTier.STANDARD],
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
        scope=_get_scope(),  # TRUST-01 T5: pamięć project_id między turami
        edit_mode=req.edit_mode,  # WRITE-02: 🟢 read blokuje zapis (autoryzacja = 🔴+PIN)
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
            system_prompt=(
                "Jesteś asystentem SmartMyOdoo. Odpowiadaj krótko i merytorycznie. "
                "Gdy pytanie dotyczy danych w Odoo (liczby rekordów, lista, pola), "
                "użyj narzędzia odoo_search (do liczby rekordów użyj pola 'count' z "
                "wyniku) lub odoo_schema. Gdy użytkownik pyta o WCZEŚNIEJSZE rozmowy lub "
                "rozwiązane problemy (np. 'czy rozmawialiśmy o', 'jak rozwiązaliśmy', "
                "'pamiętasz problem z'), użyj search_history. Nie odsyłaj do ręcznego logowania."
            ),
            # Domyślny asystent (gdy UI nie wybrał skilla) MUSI móc odpytać Odoo
            # read-only oraz przeszukać pamięć historii (MEM-01).
            allowed_tools=[
                "search_knowledge_base",
                "search_history",
                "odoo_search",
                "odoo_schema",
            ],
            red_flags=[],
            recommended_model=recommended_model,
        )

    # FIX-03: cache LLM TYLKO dla skilli read-only (świeżość danych live Odoo)
    if llm is not None and getattr(skill_config, "read_only", False):
        llm.cache = get_llm_cache()

    # ── 5. Execute (async-safe) ──
    created_proposal = None  # WRITE-02 T4: propozycja utworzona w tej turze (→ karta)
    if llm:
        from smartmyodoo.core.models import AuditLog

        try:
            exec_result = await asyncio.to_thread(
                executor.execute, skill_config, req.message
            )
            reply_text = exec_result.get("response", "Brak odpowiedzi od agenta.")
            created_proposal = exec_result.get("proposal")

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

    # ── 6b. WRITE-02 T4: propozycja z LLM → karta z diffem + 💾 Zapisz (apply+PIN) ──
    if created_proposal and created_proposal.get("proposal_id"):
        return ChatResponse(
            reply=reply_text,
            action_type="SHADOW_PROPOSAL",
            category=category_value,
            persona=persona_value,
            model=recommended_model,
            selected_skills=selected_skills_to_use,
            proposal_data=ChatProposalData(
                proposal_id=created_proposal["proposal_id"],
                text=created_proposal.get("reason") or "Propozycja zmiany w Odoo",
                model=created_proposal.get("model") or "",
                method=str(created_proposal.get("method") or "").upper(),
                args=[created_proposal.get("values") or {}],
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

    # FIX-03: rate-limit per workspace
    _enforce_chat_rate(req.workspace_id)

    vk, role, pwd = auth_data

    chat_repo = ChatRepository(db=db)

    # -- Resolve secrets from Vault (SEC-01/SEC-02) --
    vault_data = {}
    odoo_url = os.environ.get("ODOO_URL", "http://localhost:8069")
    odoo_master_pwd = os.environ.get("ODOO_MASTER_PASSWORD", "")
    odoo_db_name = os.environ.get("ODOO_DB", "odoo_prod")
    try:
        vault_data = vault.load_vault(vk)
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
    # KEY-02: klucz LLM po typie (resolver) → ENV
    openrouter_key = resolve_llm_key(vault_data, req.workspace_id)
    odoo_db_name = sanitize_db_name(odoo_db_name)  # utnij etykietę Odoo.sh

    # WSISO-02 (guard): write-path — nie-`default` bez własnego ODOO_DATA → głośny błąd,
    # NIE cichy ENV/generic (cross-client write). Kieruje url/db na instancję workspace.
    try:
        odoo_url, odoo_db_name = _resolve_write_odoo_target(
            vault_data, req.workspace_id, odoo_url, odoo_db_name
        )
    except OdooWorkspaceUnconfigured as e:
        raise HTTPException(status_code=400, detail=classify_odoo_error(e))

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
        scope=_get_scope(),  # TRUST-01 T5
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
        # FIX-04 T1 (D2): stan kłódki 🟢/🔴 z payloadu WS — parytet z REST (ChatRequest.edit_mode).
        # Fail-closed: brak pola → False (bez jawnej zgody człowieka zapis jest blokowany).
        edit_mode = bool(req_data.get("edit_mode", False))

        # 1. Auth manual (ponieważ WebSocket i headers bywają problematyczne w niektórych klientach)
        vk, role = get_auth_key(pwd)
        if not vk:
            await websocket.send_json(
                {"type": "error", "content": "Invalid credentials"}
            )
            await websocket.close(code=1008)
            return

        # FIX-03: rate-limit per workspace (WS — ręczny check, bez Depends)
        if not chat_limiter.allow(f"chat:{workspace_id or 'default'}"):
            await websocket.send_json(
                {"type": "error", "content": "Zbyt wiele żądań — spróbuj za chwilę."}
            )
            await websocket.close(code=1013)
            return

        # 2. Dispatch
        if selected_skills:
            selected_skills_to_use = selected_skills
        else:
            dispatch_result = dispatcher.classify_intent(message)
            selected_skills_to_use = (
                [dispatch_result.skill_name.value] if dispatch_result.skill_name else []
            )
        # FIX-03: model wg polityki + degradacja budżetu (K4/K5)
        _skill_for_model = selected_skills_to_use[0] if selected_skills_to_use else None
        recommended_model = effective_model(_skill_for_model, governor=_token_governor)

        # 3. LLM Key (KEY-02: resolver typowany → ENV; ADR-007)
        try:
            vault_data = vault.load_vault(vk)
        except Exception:
            vault_data = {}
        openrouter_key = resolve_llm_key(vault_data, workspace_id)
        _inject_odoo_creds(vault_data, workspace_id)  # KEY-02-3: Odoo ze Skarbca

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
            api_key=openrouter_key,
            model=recommended_model,
            governor=_token_governor,
            fallback_model=MODEL_POLICY[
                ModelTier.STANDARD
            ],  # FIX: degradacja zamiast 404
        )
        sandbox = SandboxManager()

        executor = SkillExecutor(
            llm_client=llm,
            chat_repo=chat_repo,
            workspace_id=workspace_id,
            session_id=session_id,
            sandbox=sandbox,
            pii=_get_pii(),
            scope=_get_scope(),  # TRUST-01 T5
            edit_mode=edit_mode,  # FIX-04 T1 (D2): 🟢 read blokuje zapis także w streamie
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

        # FIX-03: cache LLM tylko dla skilli read-only
        if getattr(skill_config, "read_only", False):
            llm.cache = get_llm_cache()

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
            ws_vault_data: dict = {}
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

            ws_odoo_db_name = sanitize_db_name(
                ws_odoo_db_name
            )  # utnij etykietę Odoo.sh

            # WSISO-02 (guard): write-path izolacja — jak w run_pipeline. Nie-`default`
            # bez własnego ODOO_DATA → błąd w streamie, NIE cichy ENV/generic (cross-client).
            try:
                ws_odoo_url, ws_odoo_db_name = _resolve_write_odoo_target(
                    ws_vault_data, workspace_id, ws_odoo_url, ws_odoo_db_name
                )
            except OdooWorkspaceUnconfigured as e:
                await websocket.send_json(
                    {"type": "error", "content": classify_odoo_error(e)}
                )
                return

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
        # FIX-04 T4 (A-4 / D5, ADR-011): NIE echujemy treści wyjątku do klienta —
        # str(e) może zawierać dane wrażliwe/sekrety. Do payloadu WS trafia TYLKO
        # nazwa typu (parytet z REST :339); pełny stack-trace zostaje w logu serwera.
        logger.exception("WebSocket error")
        try:
            await websocket.send_json(
                {"type": "error", "content": f"Błąd agenta: {type(e).__name__}"}
            )
        except Exception:
            pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass
