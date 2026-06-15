# 🔑 DESIGN — Typowany Rejestr Kluczy + Routing Modeli LLM

> **Status:** PROPOZYCJA (design) · **Data:** 2026-06-15 · **Autor:** `/arch`
> **Powiązania:** [HLD-TECHNICAL](../blueprint/tom2-architektura/HLD-TECHNICAL.md) · sprint [FIX-02 → S5.1](../sprints/2026-06-15_SPRINT-FIX-02_struktura_patterny.md) · `vault.py`, `swarm/dispatcher.py`, `mcp/token_governor.py`
> **Problem do rozwiązania:** dziś klucze rozpoznawane są po *magicznej nazwie* (`OPENROUTER_KEY`, `{ws}_ODOO`); brak typów, brak wyboru modelu, brak optymalizacji kosztów.

---

## 1. Analiza — JAK JEST DZIŚ

### 1.1 Rozpoznawanie kluczy = po nazwie (magic strings)
| Przeznaczenie | Wymagana nazwa sekretu | Kod |
|---|---|---|
| Model LLM | `OPENROUTER_KEY` (literalnie) | `vault_data.get("OPENROUTER_KEY")` (api.py) |
| Odoo (dane + czas pracy łącznie) | `{workspace}_ODOO` → fallback `default_ODOO` | `_get_odoo_connector` |

### 1.2 Wybór modelu = sztywna `ROUTING_TABLE` (dispatcher.py)
Intencja (A–H) → na sztywno przypisany model, np. `A_CODE → claude-3.5-sonnet`, `H_GENERAL → llama-3.1-8b`. Bez konfiguracji, bez nadpisania per workspace, z **niespójnymi ID** (`claude-3-opus-20240229` vs `anthropic/claude-3.5-sonnet` vs `openrouter/...`).

### 1.3 Wady (dlaczego to boli)
- 🔴 **Kruche** — literówka w nazwie (`openruter`) = klucz niewidzialny.
- 🔴 **Nieczytelne** — użytkownik musi znać magiczne nazwy; UI nie podpowiada.
- 🔴 **Nieskalowalne** — 100 kluczy / wielu providerów (Anthropic, OpenAI…) bez mapowania „klucz → przeznaczenie".
- 🔴 **Brak wyboru modelu** — nie da się powiedzieć „tani model do prostych rzeczy, drogi do trudnych" inaczej niż edytując kod.
- 🔴 **Jedno Odoo** — brak rozdziału: Odoo **klienta** (dane) vs Odoo **rozliczeniowe** (Twoje karty czasu pracy mogą być w INNYM systemie).

---

## 2. Projekt — JAK POWINNO BYĆ

### 2.1 Typowany Rejestr Kluczy (≥3 typy, koniec magic-names)
Każdy sekret dostaje **jawny typ i metadane**, zamiast być rozpoznawany po nazwie:

```python
class CredentialType(str, Enum):
    ODOO_DATA       = "odoo_data"        # Odoo KLIENTA — czytanie/zapis danych
    ODOO_TIMESHEET  = "odoo_timesheet"   # Odoo do logowania CZASU PRACY (może być inne)
    LLM_PROVIDER    = "llm_provider"     # klucz do modeli AI

class Credential(BaseModel):
    name: str                      # dowolna etykieta dla człowieka ("Klient ACME prod")
    type: CredentialType           # ← TO decyduje do czego służy (nie nazwa!)
    workspace_id: str = "default"
    provider: str | None = None    # dla LLM: "openrouter" | "anthropic" | "openai"
    # połączenie (Odoo):
    url: str | None = None
    db: str | None = None
    login: str | None = None
    password: str | None = None    # szyfrowane w Vault
    # LLM:
    api_key: str | None = None     # szyfrowane w Vault
    # binding (timesheet):
    default_project_ref: str | None = None
    default_task_ref: str | None = None
    enabled: bool = True
```

**3 typy = 3 przeznaczenia:**
| Typ | Do czego | Kluczowe pola |
|---|---|---|
| `odoo_data` | Odoo klienta — agent czyta/pisze dane (CRUD, ETL, audyt) | url, db, login, password |
| `odoo_timesheet` | Odoo gdzie zapisujesz **godziny pracy** (osobne konto/instancja) | url, db, login, password, default_project_ref, default_task_ref |
| `llm_provider` | klucz do modeli AI | provider, api_key |

> Rozdział `odoo_data` vs `odoo_timesheet` rozwiązuje realny scenariusz: dane są w Odoo **klienta**, a swój czas logujesz do **własnego/rozliczeniowego** Odoo — dwa różne połączenia, dwa typy.

### 2.2 Resolver — wybór po TYPIE, nie po nazwie
```python
def resolve_credential(vault, type: CredentialType, workspace_id: str, provider: str | None = None):
    cands = [c for c in vault.values()
             if c.get("type") == type and c.get("enabled", True)
             and c.get("workspace_id") in (workspace_id, "default")]
    if provider:
        cands = [c for c in cands if c.get("provider") == provider]
    # preferuj dopasowanie do workspace nad 'default'
    cands.sort(key=lambda c: 0 if c["workspace_id"] == workspace_id else 1)
    return cands[0] if cands else None
```
→ Nazwa sekretu staje się **tylko etykietą dla człowieka**. 100 kluczy, dowolnie nazwanych — system trafia po `type`+`workspace`+`provider`.

### 2.3 Routing modeli LLM + optymalizacja kosztów
Konfigurowalna mapa **funkcja/skill → poziom modelu**, z fallbackiem i budżetem:

```python
class ModelTier(str, Enum):
    CHEAP   = "cheap"    # proste: klasyfikacja, formatowanie, krótkie odpowiedzi
    STANDARD= "standard" # typowy dev/CRUD
    PREMIUM = "premium"  # architektura, trudny debug, długi kontekst

# Konfiguracja (per workspace, edytowalna w UI — nie w kodzie):
MODEL_POLICY = {
    ModelTier.CHEAP:    "openrouter/meta-llama/llama-3.1-8b-instruct",
    ModelTier.STANDARD: "openrouter/anthropic/claude-3.5-haiku",
    ModelTier.PREMIUM:  "openrouter/anthropic/claude-3.5-sonnet",
}
# Mapowanie: która funkcja/skill jakiego poziomu wymaga
SKILL_TIER = {
    "classify_intent":      ModelTier.CHEAP,     # Dispatcher = zawsze tani
    "odoo_business_analyst":ModelTier.STANDARD,
    "odoo_developer":       ModelTier.STANDARD,
    "software_architecture":ModelTier.PREMIUM,
    "financial_audit":      ModelTier.PREMIUM,
}
```

**Zasady (best practice):**
1. **Dispatcher zawsze CHEAP** — klasyfikacja intencji to prosta robota; nie marnuj Sonneta na wybór kategorii.
2. **Tier per skill, nie per intencja** — skill zna swoją złożoność.
3. **Override per workspace + per request** — user może wymusić model (gdy chce).
4. **Fallback** — gdy model/provider niedostępny → `litellm.Router` próbuje następny (S5.1).
5. **Budżet twardy** — `TokenGovernor` pre-flight: jeśli zostało mało, **degraduj do tańszego tier** zamiast blokować (graceful degradation).
6. **Cache** (Redis) na identyczne zapytania (np. powtarzalne klasyfikacje).

### 2.4 Spójne ID modeli
Wymóg: jeden format z prefiksem providera (`openrouter/<provider>/<model>`), walidowany przy zapisie. Koniec `claude-3-opus-20240229` bez prefiksu.

---

## 3. UI — koniec zgadywania nazw
Formularz „Dodaj Sekret" zyskuje:
- **Dropdown „Typ"** → `Odoo (dane)` / `Odoo (czas pracy)` / `Model AI (LLM)`.
- Pola **dynamiczne** zależne od typu (LLM: provider + api_key; Odoo: url/db/login/hasło; timesheet: + projekt/zadanie).
- Osobna sekcja **„Modele AI"**: wybór modelu per poziom (CHEAP/STANDARD/PREMIUM) + podgląd kosztu/1k tokenów + miesięczny budżet.
- Lista kluczy pokazuje **ikonę typu + przeznaczenie**, nie tylko nazwę.

---

## 4. Migracja (bez utraty danych)
1. Dodaj pola `type`/`provider` do modelu sekretu (opcjonalne).
2. **Auto-tagowanie istniejących** przy odczycie: nazwa `OPENROUTER_KEY` → `type=llm_provider, provider=openrouter`; `*_ODOO` → `type=odoo_data`. (kompatybilność wsteczna)
3. Resolver: najpierw po `type`; fallback na starą magic-name dla nieotagowanych.
4. UI prosi o uzupełnienie typu dla „osieroconych" sekretów (np. `9879879`, `nazwa 1`).

---

## 5. Plan wdrożenia (rozszerza S5.1)
| # | Zadanie | Test dowodowy |
|---|---|---|
| K1 | Model `Credential` + `CredentialType` + walidacja | unit: typ wymagany; LLM wymaga provider+api_key |
| K2 | `resolve_credential(type, ws, provider)` + auto-tag legacy | test: 2 klucze llm różnych providerów → wybór po provider; `*_ODOO` auto-otagowany |
| K3 | `odoo_timesheet` osobny od `odoo_data` w timesheet flow | test: timesheet używa `odoo_timesheet`, CRUD używa `odoo_data` |
| K4 | `ModelTier` + `SKILL_TIER` + resolver modelu (per skill, override) | test: classify→CHEAP; architektura→PREMIUM; override wymusza |
| K5 | `litellm.Router` retry/fallback/cache + spójne ID + governor degradacja | test: 429→retry; budżet niski→tier↓ zamiast block |
| K6 | UI: dropdown typ + sekcja Modele AI | e2e: dodanie LLM/Odoo przez typ, nie nazwę |

---

## 6. Werdykt
**Dziś:** rozpoznawanie po magicznej nazwie — kruche, nieskalowalne, bez wyboru modelu i kontroli kosztów per zadanie.
**Cel:** **typowany rejestr** (`odoo_data` / `odoo_timesheet` / `llm_provider`) + **resolver po typie** + **routing modeli per skill z poziomami kosztów** (tani↔drogi) + budżet z graceful degradation + spójne ID + UI z dropdownem.
**Efekt biznesowy:** 100 kluczy dowolnie nazwanych po prostu działa; tanie modele robią proste rzeczy (niższy koszt AI); rozdział Odoo klienta vs rozliczeniowego.
