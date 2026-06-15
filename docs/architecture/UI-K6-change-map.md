# 🖥️ Mapa zmian UI — K6 (rejestr kluczy + modele) w panelu graficznym

> Konkretne miejsca w `smartmyodoo/ui/index.html` (+ `ui/js/`), które zmienia K6 sprintu [KEY-01](../sprints/2026-06-15_SPRINT-KEY-01_credentials_model_routing.md).
> Stan obecny: zakładki **Skarbiec · Czat · Aktywność · Projekt · Skille**; formularz „Dodaj Sekret" (`#secret-modal`).

## A. Zakładka **Skarbiec** → formularz „Dodaj Sekret" (`#secret-modal`)
| # | Gdzie (element/selektor) | Co się zmieni |
|---|---|---|
| A1 | **NOWE** `#f-type` (dropdown), na górze, przed `#f-name` | wybór **Typu**: `Odoo (dane)` / `Odoo (czas pracy)` / `Model AI` |
| A2 | **NOWE** `#f-provider` (dropdown) | tylko dla typu LLM: `openrouter` / `anthropic` / `openai` |
| A3 | `#f-apikey` | widoczne **tylko** dla `Model AI` |
| A4 | `#f-url`, `#f-db`, `#f-login`, `#f-password` | widoczne **tylko** dla typów Odoo |
| A5 | **NOWE** `#f-project-ref`, `#f-task-ref` | tylko dla `Odoo (czas pracy)` |
| A6 | `saveSecret()` (`ui/js`) | dosyła `type` + `provider` (+project/task) do `POST /api/secrets` |
| A7 | render listy sekretów | ikona/etykieta typu obok nazwy: 🔑 LLM · 🗄️ Odoo dane · ⏱️ Odoo czas |

### Mockup nowego formularza
```
┌── Dodaj Sekret ──────────────────────────┐
│ Typ:        [ Model AI            ▼]  ← A1│
│ Nazwa:      [ ____________________ ]      │
│ Provider:   [ openrouter          ▼]  ← A2 (tylko LLM)
│ API Key:    [ ******************** ]  ← A3 (tylko LLM)
│ ─ pola Odoo (ukryte dla LLM) ─       ← A4
│ URL/Baza/Login/Hasło: [ ... ]            │
│ Projekt/Zadanie: [ ... ]             ← A5 (tylko „czas pracy")
│            [ Zapisz do Skarbca ]         │
└──────────────────────────────────────────┘
```

## B. **NOWA zakładka „⚙️ Modele"** (nav, obok Skille) — lub sekcja w „Projekt/Settings"
| # | Element | Co |
|---|---|---|
| B1 | `#tab-models` (nowa zakładka) | panel polityki modeli |
| B2 | 3× dropdown: model dla **CHEAP / STANDARD / PREMIUM** | mapuje `MODEL_POLICY` (dziś z ENV → z UI) |
| B3 | input **Budżet (USD)** + podgląd **wydane** | `MAX_BUDGET_USD` + `TokenGovernor.spent` |
| B4 | (zaawansowane) tabela **skill → poziom** | edycja `SKILL_TIER` |

→ Wymaga backendu: `GET/PUT /api/models/policy` (odczyt/zapis polityki + budżetu).

## C. Panel **Czat** (`#tab-chat`)
| # | Element | Co |
|---|---|---|
| C1 | badge przy odpowiedzi | który **model** obsłużył (pole `model` już jest w odpowiedzi `/api/chat`) |
| C2 | wskaźnik kosztu sesji | `spent` z governora (opcjonalnie) |

## Podsumowanie — gdzie co
```
Skarbiec  → formularz: dropdown Typ + pola dynamiczne + ikony typu na liście   (A)
Modele    → NOWA zakładka: wybór modelu per poziom + budżet                    (B)  [+ backend /api/models/policy]
Czat      → badge modelu + koszt sesji                                         (C)
```

> Zależności: A/C bazują na istniejącym backendzie (K1-K4 gotowe). B wymaga nowego endpointu polityki modeli (rozszerzenie K5/K6).
