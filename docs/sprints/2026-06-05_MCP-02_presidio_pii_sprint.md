# 🚀 Sprint: [MCP-02] Presidio PII Middleware

> **Architekt:** /arch | **Tryb:** Sequential
> **Data:** 2026-06-05 | **Bazuje na:** Faza 4 (Conductor)

---

## 📋 Sekcja A — Business Discovery & Rules

### Cel biznesowy
Zgodność z RODO i standardami bezpieczeństwa przy pracy z agentami LLM. Musimy wdrożyć warstwę middleware (Microsoft Presidio), która automatycznie wychwytuje i podmienia (pseudonimizuje) dane osobowe (PII) z bazy Odoo, zanim trafią do zewnętrznego modelu językowego, a następnie przywraca te dane przy zwrotnej odpowiedzi.

### Metryka sukcesu (DoD)
Dla tekstu "Jan Kowalski (NIP 1234567890)" system wysyła do LLM "<PERSON_1> (NIP <NIP_1>)", a po odpowiedzi od LLM bezbłędnie podmienia tagi z powrotem na oryginalne dane, nie zostawiając PII w żadnych logach audytowych.

### ⚖️ ZASADY SPRINTU — Podsumowanie dla Użytkownika

#### Zasada 1: SEQUENTIAL GATE (Bramka Sekwencyjna) 🔴
Każda faza kończy się bramką testową. Nie piszemy kodu dla Fazy 2, dopóki Faza 1 nie przejdzie testów PII.

#### Zasada 2: TDD FIRST / VALIDATION 🟠
Test Driven Development: najpierw piszemy `test_pii.py` jako RED (oblewające), następnie weryfikujemy, czy zaimplementowane rozpoznawacze (`PeselRecognizer`, `NipRecognizer`) poprawnie sprawiają, że test przechodzi na GREEN.

#### Zasada 3: IN-MEMORY MAPPING 🔴
Mapa odwracania tokenów PII (Token → Original Value) znajduje się *wyłącznie* w krótkotrwałej pamięci dla danej sesji u Agenta i nigdy nie jest zapisywana do SQLite ani przesyłana z logami FSM.

---

## 🧱 Sekcja B — Podział Zadań

### Graf zależności między Fazami

```
┌──────────────────────────────────────┐
│  FAZA 1: Presidio & Custom Detectors │
│  [Instalacja i Recognizery PL]       │
└──────────────┬───────────────────────┘
               │ ✅ BRAMKA: Unit test NIP/PESEL przechodzi
               ▼
┌──────────────────────────────────────┐
│  FAZA 2: Reversible Middleware       │
│  [Anonimizacja i Deanonimizacja]     │
└──────────────┬───────────────────────┘
               │ ✅ BRAMKA: Test "Roundtrip" (Tekst->Token->Tekst)
               ▼
┌──────────────────────────────────────┐
│  FAZA 3: Integracja z Agent Swarm    │
│  [Podpięcie do potoku i logów]       │
└──────────────────────────────────────┘
```

---

### Sekcja B1 — FAZA 1: Presidio Setup & Recognizers

> **📁 Scope:** `smartmyodoo/security/pii/`, `tests/security/`

| # | Zadanie | DoD | Status |
|---|---------|-----|--------|
| 1.1 | Aktualizacja zależności | Dodanie `presidio-analyzer` i `presidio-anonymizer` w `requirements.txt` / `pyproject.toml` | [ ] |
| 1.2 | `test_recognizers.py` (RED) | Testy wymagające rozpoznania polskiego NIP, PESEL i polskiego imienia w ciągach tekstowych. | [ ] |
| 1.3 | Custom Recognizers | Klasy `NipRecognizer` oraz `PeselRecognizer` oparte na RegEx, rozszerzające `EntityRecognizer` Presidio. | [ ] |
| 1.4 | **BRAMKA:** Weryfikacja | ✅ `pytest tests/security/test_recognizers.py` przechodzi. | [ ] |

---

### Sekcja B2 — FAZA 2: Reversible Anonymization Middleware

> **📁 Scope:** `smartmyodoo/security/pii/middleware.py`

| # | Zadanie | DoD | Status |
|---|---------|-----|--------|
| 2.1 | `test_middleware.py` (RED) | Test pełnego cyklu `anonymize` → `deanonymize`. | [ ] |
| 2.2 | In-memory Mapper | Klasa rejestrująca `"<NIP_1>": "1234567890"` trzymająca stan na czas wywołania agenta. | [ ] |
| 2.3 | Presidio Anonymizer Wrapper | Obudowa narzędzi Presidio w ujednolicony pipeline `PiiMiddleware`. | [ ] |
| 2.4 | **BRAMKA:** Roundtrip Test | ✅ Zanonimizowany string zawsze powraca do oryginału bez wycieków. | [ ] |

---

### Sekcja B3 — FAZA 3: Integracja z Agent Swarm

> **📁 Scope:** `smartmyodoo/swarm/pipeline.py`, `smartmyodoo/hub/`

| # | Zadanie | DoD | Status |
|---|---------|-----|--------|
| 3.1 | Podpięcie pod Swarm Pipeline | Tekst do LLM przepływa najpierw przez `pii_middleware.anonymize()`, a odpowiedź przez `deanonymize()`. | [ ] |
| 3.2 | Flaga w Workspaces | Dodanie flagi bazodanowej do `Workspace` pozwalającej opcjonalnie włączyć/wyłączyć ten moduł (dla środowisk testowych). | [ ] |
| 3.3 | Logowanie (Sanityzacja) | Upewnienie się, że `project_logger.py` loguje zawsze wartości **po** zanonimizowaniu. | [ ] |
| 3.4 | **BRAMKA:** System Test | ✅ Wykonanie zapytania LLM w pełni przez Swarm Pipeline maskuje dane lokalnie. | [ ] |

## Open Questions

> [!IMPORTANT]
> Czy w Fazie 1, oprócz NIP, PESEL i Imion, chcemy od razu dodać polskie rozpoznawacze dla Numerów Dowodu Osobistego, czy standardowy pakiet na początek nam wystarczy?

> [!WARNING]
> Czy w Fazie 3 flaga bezpieczeństwa (PII Enabled) powinna być **włączona domyślnie** dla każdej nowej przestrzeni roboczej w TeamEngine Hub? (Zalecane)
