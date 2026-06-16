---
sprint_id: "ANALYSIS-FOLLOWUPS"
workspace: "SmartMyOdoo"
status: "ANALYSIS"
created: 2026-06-16
closed: null
goal: "Analiza: jak NAJLEPIEJ domknąć (1) głębokie i18n, (2) rate-limit /api/chat, (3) wpięcie cache LLM + effective_model"
prefix: "ANALYSIS"
tags: ["analiza", "i18n", "rate-limit", "cache", "llm"]
---

# 🔎 Analiza follow-upów: i18n (głębokie) · rate-limit czatu · cache LLM

> Analiza wykonawcza — rekomendacje + plan, bez wdrożenia. Oparta na realnym kodzie (stan: main `c12c54c`).

---

## A. Głębokie i18n (pozostałe stringi)

### Stan faktyczny
- Pokryte: nav, login, Skarbiec (część), dokumentacja (pełna PL/EN), czat, aktywność, skille, projekt (kluczowe).
- **Niepokryte (~48 w `index.html`)**: modale (Dodaj Sekret — pola/labelki, Nowa Przestrzeń, Zmiana PIN), ekran **Projekt** (formularz połączenia, nagłówki stanów), sidebar, placeholdery, część komunikatów.
- Backend zwraca też PL: opisy person (`/api/skills` tooltips), komunikaty błędów API.

### Problem
Ręczne wyszukiwanie „co jeszcze nie przetłumaczone" jest zawodne i łatwo o regresję (nowy literał PL bez `t()`).

### Rekomendacja (best practice) — **guard-first**
1. **Test-strażnik** (`tests/test_i18n_coverage.py`): skanuje `index.html` (widoczne teksty / `placeholder=` z polskimi znakami **bez** `data-i18n`/`-ph`) oraz komponenty `.js` (literały z PL diakrytykami poza `window.t(...)` i poza fallbackami `: '...'`). Z **allowlistą** wyjątków. Test pokazuje liczbę „gołych" stringów i pilnuje, by nie rosła. To czyni pokrycie **mierzalnym**.
2. **Sweep statycznego HTML**: dodać `data-i18n` / `data-i18n-ph` do modali + ekranu Projekt + sidebar; klucze do `i18n.js`. (Największy, ale mechaniczny kawałek — `applyI18n` już to obsłuży.)
3. **Modale dynamiczne** (np. tytuł `#modal-title` ustawiany JS): przełożyć na `t()` w funkcjach JS (`showSecretModal`/`editSecret`).
4. **Backend**: opisy person przenieść do klienta (lepsze — i tak są duplikowane w docs.js) **lub** słownik serwerowy wg `Accept-Language`. Błędy API: krótki słownik kodów→komunikat po stronie klienta.
5. **Skalowanie słownika**: gdy `i18n.js` urośnie — wydzielić per język do `i18n/pl.json` + `i18n/en.json` (fetch przy starcie). Na teraz inline OK.

### Pułapki
- Liczenie „gołych" stringów musi pomijać fallbacki `window.t ? ... : 'PL'` (to NIE brak tłumaczenia).
- Plural PL (1/2/5) — dla liczników (np. „Wybrano: N") rozważyć `Intl.PluralRules` przy konkretnym przypadku.

### Plan
I18N-02a (test-strażnik + baseline) → 02b (modale + Projekt + sidebar) → 02c (modale dynamiczne JS) → 02d (backend / Accept-Language).

---

## B. Rate-limit `/api/chat`

### Stan faktyczny
- Jest `_AuthRateLimiter` (`api_routers/auth.py`) — **fixed-window lockout** per IP (5 prób/300s) dla logowania. Semantyka **lockout** (blokada na okno) — dobra dla brute-force, **zła dla czatu** (nie chcemy blokować użytkownika na 5 min po 5 wiadomościach).
- Endpointy LLM (`/api/chat`, `/api/pipeline/run`, WS `/api/chat/stream`) **bez** limitu częstotliwości.

### Co chcemy
Throttling: np. **N żądań / okno** per tożsamość (workspace + rola/IP), z odpowiedzią **429 + Retry-After**, bez trwałego lockoutu. Cel: ochrona przed zalaniem (koszt/DoS), komplementarna do `TokenGovernor` (koszt) i distributed lock (TOCTOU).

### Rekomendacja (best practice)
1. **Wspólny `RateLimiter`** w `core/ratelimit.py` — **sliding window** lub **token-bucket**:
   - **Redis** (multi-worker): atomowy `INCR` + `EXPIRE` (sliding-window-counter) albo token-bucket w Lua. Klucz: `rl:chat:{workspace}:{identity}`.
   - **Fallback proces-lokalny** (jak `core/lock.py`) gdy brak Redisa — spójny wzorzec.
2. **Dependency FastAPI**: `Depends(chat_rate_limit)` na endpointach czatu; przy przekroczeniu `HTTPException(429, headers={"Retry-After": ...})`. WS: ręczny check po `accept()` (jak auth).
3. **Konfiguracja ENV**: `CHAT_RATE_MAX` (np. 30), `CHAT_RATE_WINDOW_S` (np. 60). Rozsądne domyślne.
4. **Tożsamość**: workspace_id + (rola/IP). Per-workspace lepsze niż globalne IP (multi-tenant).

### Dlaczego NIE rozszerzać `_AuthRateLimiter`
Inna semantyka (lockout vs throttle) i inny storage (in-proc vs Redis multi-worker). Lepszy osobny, reużywalny komponent; `_AuthRateLimiter` zostaje do logowania.

### Plan
FIX-03a: `core/ratelimit.py` (Redis + fallback) + testy (przekroczenie → 429; reset po oknie) → FIX-03b: dependency na `/api/chat` + `/api/pipeline/run` + WS.

---

## C. Wpięcie cache LLM + `effective_model`

### Stan faktyczny
- S5.1 dostarczyło `core/llm_cache.py` (InMemory/Redis) + `OpenRouterClient(cache=, temperature=, max_tokens=, backoff_base=)`, ale w `api_routers/chat.py` klient tworzony **3× BEZ `cache=`** (cache nieużywany w produkcji).
- K5 dostarczyło `model_policy.effective_model(skill, governor)` (degradacja tieru przy niskim budżecie) — **nigdzie nie wywołane** (handler używa `recommended_model` z dispatchera).

### Ryzyka cache (kluczowe!)
1. **Świeżość**: zapytania „pokaż aktualny stan X" z cache zwrócą **stare** dane → mylące. Cache odpowiedzi LLM nadaje się do **deterministycznych/wiedzowych** zapytań, nie do odczytów live z Odoo.
2. **Tool-calls / efekty uboczne**: cachowana odpowiedź z `tool_calls` → executor i tak wykona narzędzia; cachujemy decyzję LLM, ale dla operacji zapisu/Shadow lepiej **nie** cachować.
3. **PII/izolacja**: klucz budowany z **pseudonimizowanych** wiadomości (per workspace tokeny `<PERSON_1>` różne) → naturalna izolacja między workspace'ami. OK, ale potwierdzić w teście.
4. **Multi-worker**: InMemory nie współdzieli się między procesami → w produkcji **Redis**.

### Rekomendacja (best practice) — **konserwatywnie, opt-in**
1. **Provider cache** w `chat_deps.py`: `get_llm_cache()` → `RedisLLMCache` gdy `REDIS_URL`, inaczej `InMemoryLLMCache` (lub `None` gdy wyłączony ENV `LLM_CACHE=off`).
2. **Cachuj tylko bezpieczne przypadki**: flaga `SkillConfig.cacheable` (domyślnie **False**); cache podpinany do `OpenRouterClient` **tylko** dla skilli read-only/wiedzowych (np. `software_architecture`, `ODOO_BUSINESS_ANALYST` bez narzędzi). Albo prościej: cache tylko gdy `tools` puste + krótki **TTL** (np. 300s).
3. **`effective_model`**: w handlerze chatu zamień `recommended_model` → `effective_model(skill, governor=_token_governor)` — łączy degradację budżetu (K5) z produkcją. Niskie ryzyko, duża wartość.
4. **Metryki**: log cache hit/miss + degradacji (do Aktywności/monitoringu).

### Dlaczego nie „cache wszystkiego"
Cache na ścieżce z danymi live Odoo = ryzyko podania nieaktualnych danych jako pewnik. Lepszy wąski, świadomy zakres + TTL niż globalne cache.

### Plan
FIX-03c: `get_llm_cache()` + wpięcie `cache=` warunkowo (tools puste / `cacheable`) + TTL → FIX-03d: `effective_model` w handlerze + test (degradacja przy niskim budżecie wybiera tańszy tier) → FIX-03e: metryki hit/miss.

---

## 📌 Rekomendowana kolejność (wartość/ryzyko)
1. **`effective_model` w handlerze** (C4) — mały, duża wartość (budżet→tańszy model), niskie ryzyko.
2. **Rate-limit czatu** (B) — ochrona kosztów/DoS, czysty reużywalny komponent.
3. **Cache LLM warunkowo** (C1-C2) — wartość kosztowa, ale wymaga ostrożności (świeżość) — wąski zakres + TTL.
4. **i18n guard + sweep** (A) — równolegle, mechaniczne, mierzalne testem.

> Każdy punkt = osobny PR z testem dowodowym (Evidence Before Claims), zero zmian zachowania domyślnego bez jawnej konfiguracji.
