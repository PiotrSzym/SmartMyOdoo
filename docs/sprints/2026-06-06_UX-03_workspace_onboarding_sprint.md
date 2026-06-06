# 🚀 Sprint: UX-03 — Secure Workspace Onboarding

> **Architekt:** /arch | **Tryb:** Sequential
> **Data:** 2026-06-06 | **Bazuje na:** UX-02 (Persistence & Security Cleanup)
> **Status:** 📋 DO ZATWIERDZENIA

---

## 📐 ADR-UX-03: Vanishing Credentials Pattern

### Kontekst
Przy tworzeniu nowej Przestrzeni Roboczej (Workspace) użytkownik musi obecnie
wykonać dwa oddzielne kroki: (1) utworzyć workspace podając ID/Nazwę/URL, a następnie
(2) przejść do widoku Vault i ręcznie dodać sekrety (login, hasło, API key) przypisując
im ten sam `workspace_id`. To prowadzi do "osieroconych" workspace'ów bez poświadczeń
i łamie zasadę Zero-Trust (dane wrażliwe tymczasowo egzystują jako luźne pojęcia
w głowie użytkownika, zamiast być od razu zaszyfrowane).

### Decyzja
Wdrażamy wzorzec **"Vanishing Credentials"** (Znikające Poświadczenia):

1. Modal tworzenia Workspace zostaje rozbudowany o sekcję opcjonalnych pól
   na poświadczenia (identyczną strukturę jak w modalu "Dodaj Sekret"):
   `Login`, `Hasło/Token`, `API Key`, `Data ważności`.

2. Po kliknięciu "Utwórz Przestrzeń":
   - **Krok A (SQLite):** Metadane workspace (`id`, `name`, `odoo_url`) trafiają
     do tabeli `workspaces` w bazie relacyjnej.
   - **Krok B (Vault):** Jeśli użytkownik wypełnił pola poświadczeń, backend
     automatycznie tworzy wpis w zaszyfrowanym Vault o nazwie `{workspace_id}_ODOO`
     z polami `login`, `password`, `api_key`, `url=odoo_url`, `workspace_id`.
   - **Krok C (DOM Cleanup):** Frontend czyści wszystkie pola formularza z pamięci
     DOM. Poświadczenia **znikają z interfejsu na zawsze**.

3. Po utworzeniu, w widoku Settings danego Workspace, wyświetlane jest **wyłącznie**
   pole `URL Odoo` (metadana, niezaszyfrowana). Zarządzanie poświadczeniami
   (edycja, podgląd, usunięcie) odbywa się **wyłącznie przez widok Vault**
   po przełączeniu na dany workspace w sidebarze.

### Konsekwencje
- ✅ Poświadczenia nigdy nie trafiają do SQLite (nawet tymczasowo)
- ✅ Użytkownik ma w pełni funkcjonalny workspace po jednym kliknięciu
- ✅ Separacja warstw: SQLite = metadane, Vault = sekrety (Zero-Trust)
- ⚠️ Użytkownik musi wiedzieć, że edycja poświadczeń wymaga przejścia do Vault
  (rozwiązane przez link "Zarządzaj sekretami w Vault →" w widoku Settings)

### Status
**PROPOZYCJA** — Oczekuje zatwierdzenia użytkownika.

---

## 📋 Sekcja A — Business Discovery & Rules

### Cel biznesowy
Umożliwić tworzenie w pełni skonfigurowanej Przestrzeni Roboczej (z poświadczeniami
Odoo) w jednym kroku, eliminując sieroce workspace'y. Poświadczenia są natychmiast
szyfrowane w warstwie Vault i znikają z interfejsu — dostępne tylko przez moduł
Zarządzania Sekretami.

### Metryka sukcesu (DoD)
```
python -m pytest tests/ → 50+ passed, 0 failed
+ Nowy test: test_workspace_onboarding_creates_vault_secret
+ Nowy test: test_workspace_settings_hides_credentials
+ Manualnie: Po utworzeniu workspace z hasłem → hasło widoczne TYLKO w Vault
```

### ⚖️ ZASADY SPRINTU — Podsumowanie

#### Zasada 1: SEQUENTIAL GATE (Bramka Sekwencyjna) 🔴
Fazy realizowane sekwencyjnie. Faza N+1 NIE startuje dopóki Bramka Fazy N nie jest GREEN.

#### Zasada 2: TDD FIRST / VALIDATION 🟠
Każda faza kończy się walidacją: `python -m pytest tests/` → ALL GREEN.

#### Zasada 3: SCOPE ISOLATION 🔴
- **Faza 1:** `smartmyodoo/api.py`, `smartmyodoo/vault/schemas.py`
- **Faza 2:** `smartmyodoo/ui/index.html` (modal workspace)
- **Faza 3:** `smartmyodoo/ui/index.html` (widok settings), `smartmyodoo/ui/js/`
- **Faza 4:** `tests/test_api.py`

---

## 🧱 Sekcja B — Podział Zadań

### Graf zależności między Fazami

```
┌──────────────────────────────────────────────────────────────┐
│  FAZA 1: Backend — Rozszerzenie POST /api/workspaces         │
│  1.1  Nowy schema: WorkspaceCreateRequest (z opcjonal. creds)│
│  1.2  Logika Vault-inject w create_workspace()               │
└──────────────────┬───────────────────────────────────────────┘
                   │ ✅ BRAMKA: pytest ALL GREEN
                   ▼
┌──────────────────────────────────────────────────────────────┐
│  FAZA 2: Frontend — Rozbudowa Modala "Nowa Przestrzeń"       │
│  2.1  Dodanie sekcji "Poświadczenia (zapisywane w Vault)"    │
│  2.2  Aktualizacja saveWorkspace() o nowe pola               │
└──────────────────┬───────────────────────────────────────────┘
                   │ ✅ BRAMKA: Modal renderuje pola + payload zawiera creds
                   ▼
┌──────────────────────────────────────────────────────────────┐
│  FAZA 3: UX — Widok Settings (ukrycie poświadczeń)           │
│  3.1  Settings wyświetla TYLKO URL Odoo (bez login/pass)     │
│  3.2  Link "Zarządzaj sekretami w Vault →"                  │
└──────────────────┬───────────────────────────────────────────┘
                   │ ✅ BRAMKA: Brak wycieków creds w Settings DOM
                   ▼
┌──────────────────────────────────────────────────────────────┐
│  FAZA 4: Testy integracyjne                                  │
│  4.1  test_workspace_onboarding_creates_vault_secret         │
│  4.2  test_workspace_onboarding_no_creds_still_works         │
│  4.3  test_workspace_settings_hides_credentials              │
└──────────────────────────────────────────────────────────────┘
```

---

### Sekcja B1 — FAZA 1: Backend — Rozszerzenie API

> **Trigger:** `/dev go`
> **📁 Scope:** `smartmyodoo/api.py`, `smartmyodoo/vault/schemas.py`

| # | Zadanie | DoD | Status |
|---|---------|-----|--------|
| 1.1 | **Nowy Pydantic model** `WorkspaceCreateRequest` w `schemas.py` z polami: `id`, `name`, `odoo_url`, `admin_login?`, `admin_password?`, `admin_api_key?`, `admin_expires?` | Model importowalny, walidacja działa | [ ] |
| 1.2 | **Logika dual-write** w `create_workspace()`: po zapisie metadanych do SQLite, jeśli `admin_password` jest niepuste → wywołaj `vault.load_vault(vk)` i dodaj wpis `{ws_id}_ODOO` z polami login/password/api_key/url/workspace_id, potem `vault.save_vault(vk, data)` | Sekret pojawia się w Vault | [ ] |
| 1.3 | Endpoint akceptuje zarówno stary format (bez creds) jak i nowy (z creds) — backwards compatible | Istniejące testy nadal GREEN | [ ] |
| 1.4 | **BRAMKA:** `python -m pytest tests/` | ✅ ALL GREEN (50+ passed) | [ ] |

**Szczegóły techniczne:**
```python
# schemas.py — nowy model
class WorkspaceCreateRequest(BaseModel):
    id: str
    name: str
    odoo_url: str = ""
    # Opcjonalne poświadczenia (Vanishing Credentials)
    admin_login: Optional[str] = None
    admin_password: Optional[str] = None
    admin_api_key: Optional[str] = None
    admin_expires: Optional[str] = None

# api.py — logika dual-write (pseudokod)
@app.post("/api/workspaces")
async def create_workspace(
    ws: WorkspaceCreateRequest,
    auth_data = Depends(require_auth),
    db: Session = Depends(get_db)
):
    # Krok A: SQLite (metadane)
    new_ws = db_models.Workspace(id=ws.id, name=ws.name, odoo_url=ws.odoo_url)
    db.add(new_ws); db.commit()

    # Krok B: Vault (poświadczenia) — jeśli podane
    if ws.admin_password:
        vk, _, _ = auth_data
        vault_data = vault.load_vault(vk)
        vault_data[f"{ws.id}_ODOO"] = {
            "password": ws.admin_password,
            "login": ws.admin_login or "",
            "api_key": ws.admin_api_key or "",
            "url": ws.odoo_url,
            "workspace_id": ws.id,
            "expires": ws.admin_expires or "",
        }
        vault.save_vault(vk, vault_data)

    return {"success": True, "id": ws.id}
```

---

### Sekcja B2 — FAZA 2: Frontend — Rozbudowa Modala

> **📁 Scope:** `smartmyodoo/ui/index.html` (linie 236–257)

| # | Zadanie | DoD | Status |
|---|---------|-----|--------|
| 2.1 | Dodaj **rozwijaną sekcję** "🔐 Poświadczenia Odoo (zapisywane w Vault)" z polami: `Login`, `Hasło/Token` (type=password), `API Key` (type=password), `Ważność` (type=date) | Pola widoczne w modalu | [ ] |
| 2.2 | Funkcja `saveWorkspace()` zbiera nowe pola i dołącza je do payloadu JSON wysyłanego na `POST /api/workspaces` | DevTools → Network → payload zawiera `admin_login`, `admin_password` | [ ] |
| 2.3 | Po zamknięciu modala wszystkie pola password są czyszczone (`value = ''`) | Brak wycieku w DOM | [ ] |
| 2.4 | **BRAMKA:** Modal wyświetla się poprawnie, dane lecą w payloadzie | ✅ Manualna weryfikacja | [ ] |

---

### Sekcja B3 — FAZA 3: UX — Widok Settings Workspace

> **📁 Scope:** `smartmyodoo/ui/index.html`, `smartmyodoo/ui/js/components/`

| # | Zadanie | DoD | Status |
|---|---------|-----|--------|
| 3.1 | W widoku Settings danego Workspace (po kliknięciu w panelu bocznym) wyświetlaj TYLKO: `Nazwa`, `ID (readonly)`, `URL Odoo` | Brak pól login/hasło w Settings | [ ] |
| 3.2 | Pod sekcją URL dodaj link: **"🔐 Zarządzaj sekretami w Vault →"** który przełącza aktywny tab na widok Vault (filtrowany po danym workspace) | Kliknięcie otwiera Vault z sekretami workspace | [ ] |
| 3.3 | **BRAMKA:** W DOM widoku Settings nie ma żadnych pól `type=password` | ✅ Inspekcja DOM | [ ] |

---

### Sekcja B4 — FAZA 4: Testy Integracyjne

> **📁 Scope:** `tests/test_api.py`

| # | Zadanie | DoD | Status |
|---|---------|-----|--------|
| 4.1 | `test_workspace_onboarding_creates_vault_secret` — Tworzy workspace z `admin_password`, sprawdza że w `GET /api/secrets?workspace_id=X` pojawia się klucz `X_ODOO` | assert status 200, klucz obecny | [ ] |
| 4.2 | `test_workspace_onboarding_no_creds_still_works` — Tworzy workspace BEZ poświadczeń (backwards compat), sprawdza że workspace istnieje a Vault jest pusty | assert status 200, brak nowych sekretów | [ ] |
| 4.3 | `test_workspace_settings_hides_credentials` — Sprawdza że `GET /api/workspaces` NIE zawiera pól `admin_password`, `admin_login` w odpowiedzi | assert brak kluczy w JSON | [ ] |
| 4.4 | **BRAMKA FINALNA:** `python -m pytest tests/` | ✅ ALL GREEN (53+ passed) | [ ] |

---

## ✅ Sekcja E — Finalna Weryfikacja

> Wykonuje użytkownik lub `/qa` po zakończeniu wszystkich faz.

| # | Check (Core Pillars) | Komenda / Akcja | Oczekiwany wynik |
|---|----------------------|-----------------|------------------|
| V1 | Test Suite | `python -m pytest tests/` | ✅ 53+ passed, 0 failed |
| V2 | Security Audit | `grep -rn "admin_password" smartmyodoo/ui/` | ✅ 0 wyników (brak wycieków w widoku Settings) |
| V3 | Backwards Compat | Stare testy workspace_create, workspace_list | ✅ Nadal GREEN |
| V4 | Manualny Smoke Test | Utwórz workspace z creds → przejdź do Vault → sprawdź sekret | ✅ Sekret `{id}_ODOO` widoczny |
| V5 | DOM Cleanup | Po zamknięciu modala → Inspect pola password | ✅ Pola puste |

---

## 📊 Podsumowanie Zakresu Zmian

| Plik | Typ zmiany | Faza |
|------|------------|------|
| `smartmyodoo/vault/schemas.py` | MODIFY — nowy `WorkspaceCreateRequest` | F1 |
| `smartmyodoo/api.py` | MODIFY — logika dual-write w `create_workspace()` | F1 |
| `smartmyodoo/ui/index.html` | MODIFY — rozbudowa modala workspace (L236–257) | F2 |
| `smartmyodoo/ui/index.html` | MODIFY — widok Settings (link do Vault) | F3 |
| `tests/test_api.py` | MODIFY — 3 nowe testy onboarding | F4 |

**Szacowany nakład:** ~2h (4 fazy × ~30min)
