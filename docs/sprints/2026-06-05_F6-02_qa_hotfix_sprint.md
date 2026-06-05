# 🚀 Sprint: F6-02 QA Hotfix & UI Stabilization

> **Architekt:** /arch | **Tryb:** Sequential
> **Data:** 2026-06-05 | **Bazuje na:** Raport QA-02 Frontend-Backend Review

---

## 📋 Sekcja A — Business Discovery & Rules

### Cel biznesowy
Szybki Hotfix łatający luki zidentyfikowane podczas kontroli `/qa`.
Kluczowe modyfikacje to eliminacja krytycznego błędu CORS/CSRF (przez zrezygnowanie z czystego `fetch` na rzecz wbudowanego silnika `web.rpc` z frameworku Odoo) oraz poprawa UX/Bezpieczeństwa poprzez dodanie mechanizmu obronnego przed Race Condition (podwójnym klikaniem Entera).

### Metryka sukcesu (DoD)
Wysłanie wiadomości do Agenta tymczasowo blokuje input i wywołuje asynchroniczne żądanie przez natywną warstwę RPC Odoo (posiadającą wbudowane tokeny sesyjne), zapobiegając spamowaniu backendu.

### ⚖️ ZASADY SPRINTU — Podsumowanie dla Użytkownika

#### Zasada 1: Odoo Framework Native 🔴
Kategoryczny zakaz używania natywnych instrukcji `fetch` oraz `XMLHttpRequest` do komunikacji z API Odoo (Controllerów Odoo). Obowiązuje korzystanie ze standardu Odoo, czyli `const rpc = require('web.rpc')`.

#### Zasada 2: UX Guard (Zasada Jednego Kliknięcia) 🟠
Zawsze podczas asynchronicznego oczekiwania na odpowiedź sieciową należy zabezpieczyć interfejs wizualny przed ponownym zainicjowaniem akcji (`isLoading`).

---

## 🧱 Sekcja B — Podział Zadań

### Graf zależności między Fazami

```
┌──────────────────────────────────────┐
│  FAZA 1 (Frontend Hotfix)            │
│  [web.rpc + isLoading Guard]         │
└──────────────┬───────────────────────┘
               │ ✅ BRAMKA: Test w UI (brak spamu)
               ▼
┌──────────────────────────────────────┐
│  FAZA 2 (Backend Typings)            │
│  [Any w Pydantic]                    │
└──────────────────────────────────────┘
```

---

### Sekcja B1 — FAZA 1: Usunięcie luk architektonicznych Frontendu

> **📁 Scope:** `c:\od_zera_do_ai\SmartMyOdoo\custom_addons\smart_chat\static\src\components\`

| # | Zadanie | DoD | Status |
|---|---------|-----|--------|
| 1.1 | XML: Wskaźnik ładowania | Pole `input` otrzymuje blokadę `t-att-disabled="state.isLoading"`. Dodano mały tekst "Agent myśli..." jeśli isLoading to prawda. | [ ] |
| 1.2 | XML: Usunięcie martwych kodów | Usunięto nieużywany i niepotrzebny `t-ref="chatInput"`. | [ ] |
| 1.3 | JS: Inicjalizacja Stanu | Dodano pole `isLoading: false` w konstruktorze/setup. | [ ] |
| 1.4 | JS: Refactor na `web.rpc` | Usunięto `fetch`. Zaimplementowano `rpc.query({ route: '/smart_chat/send', params: {...} })`. | [ ] |
| 1.5 | JS: Blokada Promise | Zmiana `state.isLoading` na `true` przed wysyłką i na `false` w bloku `finally`. | [ ] |
| 1.6 | **BRAMKA:** Weryfikacja UI | ✅ Zablokowany interfejs podczas requestu i poprawne rozwiązanie Promise. | [ ] |

---

### Sekcja B2 — FAZA 2: Porządki w Typowaniach (Backend)

> **📁 Scope:** `c:\od_zera_do_ai\SmartMyOdoo\smartmyodoo\swarm\`

| # | Zadanie | DoD | Status |
|---|---------|-----|--------|
| 2.1 | Zmiana z `list` na `list[Any]` | W pliku `models.py` dla schematu `ChatProposalData` naprawiono linterowy warning Mypy. Zaimportowano `Any`. | [ ] |
| 2.2 | **BRAMKA:** Lint Check | ✅ Komenda `ruff check` nie wyrzuca błędów. | [ ] |

---

## ⚠️ User Review Required

> [!WARNING]
> Ten plan naprawczy (Hotfix) zmienia sposób autoryzacji do Odoo Proxy. Przejście z `fetch` na Odoo `web.rpc` narzuca format zwrotny JSON (odpowiedź w kluczu `result`). Zapewni to 100% zgodności CSRF, ale wymaga solidnej zmiany w kodzie JavaScript.
>
> Potwierdź, czy zgadzasz się z zakresem Fixów, abym mógł powołać `/dev` do natychmiastowej naprawy!
