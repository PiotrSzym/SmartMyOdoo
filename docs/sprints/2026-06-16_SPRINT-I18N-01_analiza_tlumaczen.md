---
sprint_id: "I18N-01"
workspace: "SmartMyOdoo"
status: "ANALYSIS"
created: 2026-06-16
closed: null
goal: "ANALIZA: jak przetłumaczyć całą aplikację na wiele języków (PL/EN/…) bez build-stepu"
prefix: "I18N"
complexity: 4
roadmap_ref: "Faza 8 — UX/i18n"
tags: ["i18n", "ux", "analiza", "frontend"]
---

# 🌍 Sprint: I18N-01 — Wielojęzyczność aplikacji

> **Architekt:** /arch | **Data:** 2026-06-16
>
> ## ✅ Status implementacji (PL + EN)
> - **I18N-01a (framework)** ✅ — `ui/js/i18n.js`: słownik PL/EN, `t()`, `applyI18n()` (skan `data-i18n`/`-title`/`-ph`), `AppStore.lang` + `localStorage`, **przełącznik PL/EN w nav** (`#lang-switch`).
> - **I18N-01b (statyczny HTML)** 🏗️ częściowo — przetłumaczone: pasek nav (etykiety + tooltipy), ekran logowania, przyciski Skarbca (Dokumentacja/Reset PIN/Zablokuj), zapis sekretu. Reszta modali/etykiet — do dokończenia.
> - **I18N-01d (dokumentacja)** ✅ — Centrum Dokumentacji **w pełni dwujęzyczne** (8 sekcji + 11 agentów PL/EN), przełącza się z językiem.
> - **I18N-01c (komponenty JS)** 🏗️ w toku — ✅ `chat` + `activity` (kluczowe stringi → `t()` + re-render na zmianę języka). ⬜ pozostają `skills` + `project`.
> - **I18N-01e/f** ⬜ — backend (opisy person/błędy), daty/`Intl`, testy Playwright przełączenia języka.
>
> Dowód na żywo: przełączenie EN → nav „Czat"→„Chat", docs h1 „Documentation Center", `lang` w store + localStorage.

---

## 📋 Sekcja A — Analiza stanu i podejścia

### Stan zastany (gdzie są teksty)
| Warstwa | Gdzie | Charakter |
|---|---|---|
| **Statyczny HTML** | `ui/index.html` (~1255 l.) | etykiety zakładek, modale, przyciski, nagłówki — PL na sztywno |
| **Dynamiczny JS** | `ui/js/components/*.js` (~1827 l.) | stringi budowane w JS (czat, skille, docs, toasty, błędy) |
| **Treść dokumentacji** | `docs.js` (DOCS_SECTIONS, AGENTS) | długie bloki PL |
| **Backend** | `api_routers/chat.py` (opisy skilli/tooltips), komunikaty błędów API | część tekstów wraca z serwera |

> Wniosek: ~80% tekstów jest po stronie klienta (HTML + JS). Backend zwraca trochę (opisy person, błędy) — można je też przenieść do klienta lub tłumaczyć osobno.

### Rekomendowane podejście — lekki i18n bez builda
Stack to vanilla JS + CDN (bez bundlera), więc **nie** wprowadzamy ciężkich frameworków (i18next z buildem).
Wzorzec dopasowany do projektu:

1. **Słownik** `ui/js/i18n.js`: `const I18N = { pl: {...}, en: {...} }` — klucze → tłumaczenia.
2. **Funkcja `t(key)`** + globalny stan języka w `AppStore` (`lang`, domyślnie `pl`, zapis w `localStorage`).
3. **Statyczny HTML:** atrybuty `data-i18n="klucz"` (treść) i `data-i18n-attr` (np. `title`/`placeholder`).
   Po starcie i po zmianie języka skaner `applyTranslations(root)` podstawia teksty.
4. **Dynamiczny JS:** komponenty wołają `t('klucz')` zamiast literałów; re-render po zmianie języka
   (komponenty już się przerenderowują — wystarczy subskrypcja `AppStore` na `lang`).
5. **Przełącznik języka** w pasku nav (🇵🇱/🇬🇧 lub dropdown) → `AppStore.setState({lang})` → `applyTranslations()` + powiadomienie komponentów.
6. **Dokumentacja:** `DOCS_SECTIONS`/`AGENTS` jako struktura per-język (`{pl:[…], en:[…]}`) albo osobny plik `docs.i18n.js`.

### Dlaczego tak (a nie i18next/build)
- Zero zmian w toolchainie (CDN-only), spójne z istniejącym `AppStore` (Observer) i wzorcem re-renderu komponentów.
- `data-i18n` pokrywa statyczny HTML bez przepisywania struktury; `t()` pokrywa JS.
- Łatwo dodać kolejny język = nowy klucz w słowniku.

### Pułapki
- **RTL** (arabski/hebrajski) — jeśli kiedyś, trzeba `dir="rtl"` + warianty Tailwind. Na teraz PL/EN = LTR.
- **Interpolacja** (zmienne w zdaniu) — `t('klucz', {n: 5})` z prostym zastąpieniem `{n}`.
- **Liczba mnoga** (plural rules) — dla PL nietrywialne; na start proste, potem `Intl.PluralRules`.
- **Treść backendu** (opisy person w `/api/chat`) — albo przenieść opisy do klienta (lepsze), albo dać `Accept-Language` + słownik serwera.
- **Daty/liczby** — `Intl.DateTimeFormat`/`NumberFormat` wg `lang`.

---

## 🧱 Sekcja B — Plan implementacji (fazy)

| Faza | Zakres | Szac. |
|---|---|---|
| **I18N-01a** | Szkielet: `i18n.js` (słownik PL+EN), `t()`, `AppStore.lang` (+localStorage), `applyTranslations()`, przełącznik w nav | S |
| **I18N-01b** | Pokrycie statycznego HTML — `data-i18n` na zakładkach, modalach, przyciskach, nagłówkach (`index.html`) | M |
| **I18N-01c** | Pokrycie dynamicznego JS — `t()` w `chat/skills/activity/project/docs` + re-render na zmianę języka | M |
| **I18N-01d** | Dokumentacja wielojęzyczna (`DOCS_SECTIONS`/`AGENTS` per język) | M |
| **I18N-01e** | Backend: przeniesienie opisów person do klienta / `Accept-Language`; daty/liczby przez `Intl` | S |
| **I18N-01f** | Testy: przełączenie języka zmienia widoczne teksty (Playwright); brak „gołych" literałów w nav | S |

### Rekomendowana kolejność dostarczania
I18N-01a (szkielet + przełącznik) → I18N-01b (nav + modale, natychmiast widoczny efekt) → I18N-01c → I18N-01d → I18N-01e.

---

## 🔬 Sekcja C — Definicja sukcesu
- [ ] Przełącznik języka w nav; wybór zapamiętany (localStorage).
- [ ] Zmiana języka natychmiast tłumaczy nav, modale, czat, skille, dokumentację.
- [ ] PL i EN kompletne; dodanie 3. języka = tylko nowy zestaw kluczy.
- [ ] Test Playwright: po przełączeniu na EN etykiety zakładek są po angielsku.

> **Decyzja użytkownika do podjęcia:** które języki na start (PL+EN? + DE/FR/ES?) oraz czy tłumaczymy też pełną treść Centrum Dokumentacji (duża objętość) czy tylko interfejs.
