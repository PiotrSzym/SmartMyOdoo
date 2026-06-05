# 🚀 Sprint: Premium Cyber UI (Vault GUI)

> **Architekt:** /arch | **Tryb:** Sequential
> **Data:** 2026-06-04 | **Bazuje na:** Zaktualizowanym Implementation Plan

---

## 📋 Sekcja A — Business Discovery & Rules

### Cel biznesowy
Zastąpienie prostego interfejsu CLI zaawansowanym, graficznym panelem w przeglądarce. Panel ma ułatwić manualne kopiowanie sekretów, zmianę PINu dzięki dodaniu konceptu **Master Password** oraz szybkie wyszukiwanie przy pomocy wytycznych **Standalone Analytics Standard** (estetyka Cyber BI, Dark mode, szklane karty, Tailwind). Z założenia system działa cicho w tle pod komendami Agentów, ale dla człowieka dostarcza elitarny interfejs ułatwiający pracę (Guidance z listą). Skarbiec zacznie przechowywać ustrukturyzowane metadane (Login, Hasło, URL, API Key, Ważność), zamiast płaskich tekstów.

### Metryka sukcesu (DoD)
Wywołanie `python vault.py gui` uruchamia serwer na localhost po weryfikacji Master Password. Użytkownik widzi piękny panel Cyber UI z listą i guidance, gdzie może skopiować hasło pojedynczym kliknięciem lub zmienić PIN do skarbca.

### ⚖️ ZASADY SPRINTU
#### Zasada 1: SEQUENTIAL GATE (Bramka Sekwencyjna) 🔴
Nie rozpoczynamy budowy interfejsu (Fazy 6), dopóki implementacja Architektury KEK (Key Encrypting Key) dla Master Password oraz nowy backend API nie zwrócą poprawnych wyników.

#### Zasada 2: TDD FIRST / VALIDATION 🟠
Istniejące automatyczne testy w `test_vault.py` muszą nadal działać po zmianie schematu.

---

## 🧱 Sekcja B — Podział Zadań

### Graf zależności między Fazami

```text
┌──────────────────────────────────────┐
│  FAZA 5: KEK & Backend API           │
│  [Implementacja Master Password]     │
│  [Migracja z text na JSON Schema]    │
└──────────────┬───────────────────────┘
               │ ✅ BRAMKA: Zgodność testów i autoryzacji
               ▼
┌──────────────────────────────────────┐
│  FAZA 6: Premium Cyber UI (Frontend) │
│  [index.html + TailwindCSS]          │
│  [Manualne Kopiowanie, Zmiana PIN]   │
└──────────────────────────────────────┘
```

---

### Sekcja B1 — FAZA 5: KEK & Backend API

> **Trigger:** Implementacja serwera w `vault.py`
> **📁 Scope:** `smart_vault/`

| # | Zadanie | DoD | Status |
|---|---------|-----|--------|
| 5.1 | KEK Architecture (Master Password) | Wprowadzenie Master Password zdolnego deszyfrować klucz główny (Vault Data) i zmieniać z poziomu GUI zagubiony PIN. | [x] |
| 5.2 | Migracja do struktury JSON (`vault.py`) | Komenda `add` tworzy obiekty `{password:..., login:..., ...}` zamiast stringów. | [x] |
| 5.3 | Spłaszczacz (Flattener) dla `run` | Komenda `run` spłaszcza obiekty do ENV (np. `KLUCZ_LOGIN`, `KLUCZ_PASSWORD`). | [x] |
| 5.4 | Lokalny serwer REST API | Komenda `gui` uruchamia serwer na porcie 5050. Endpointy CRUD autoryzowane Master Pass / PIN. | [x] |
| 5.5 | **BRAMKA:** Weryfikacja Logiki | ✅ Uruchomienie serwera nie psuje CLI i E2E przechodzi pozytywnie. | [x] |

---

### Sekcja B2 — FAZA 6: Premium Cyber UI (Frontend)

> **Trigger:** Sukces Fazy 5
> **📁 Scope:** `smart_vault/index.html` (or ui folder)

| # | Zadanie | DoD | Status |
|---|---------|-----|--------|
| 6.1 | Baza HTML (Cyber BI + Guidance) | Lista kluczy renderowana z estetyką #0f172a, zawierająca prosty instruktaż korzystania z sejfu dla człowieka. | [x] |
| 6.2 | Kopiowanie Manualne | Przycisk "Kopiuj" przy polach hasła z funkcją skopiowania wartości jednym kliknięciem do schowka systemu. | [x] |
| 6.3 | Modal Dodawania i Edycji | Zbudowany z glassmorphismu formularz dla pól (URL, Login, Hasło, API, Ważność). | [x] |
| 6.4 | Panel Zmiany PINu | Specjalna opcja wywoływania resetu PINu pod warunkiem podania Master Password. | [x] |
| 6.5 | **BRAMKA:** E2E User Acceptance | ✅ Wpisanie w przeglądarkę `localhost:5050` pozwala na pełne zarządzanie sejfem oraz zresetowanie PINu. | [x] |

---
