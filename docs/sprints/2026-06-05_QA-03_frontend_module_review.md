# 🕵️‍♂️ QA Review 2: F6-03 Frontend Module & Architecture

> **Tryb:** /qa | **Data:** 2026-06-05 | **Projekt:** SmartMyOdoo

Ponowny audyt plików po hotfixie (F6-02) przeprowadzony z perspektywy Senior Odoo Developera (wersja 16+).

## 🚨 Wykryte Krytyczne Błędy Architektoniczne (Module System Anti-Pattern)

### 1. 🔴 CRITICAL: Mieszanie `@odoo-module` z legacy `odoo.define`
- **Problem:** Plik `chat_widget.js` rozpoczyna się dyrektywą `/** @odoo-module **/`, co oznacza, że kompilator Odoo automatycznie wrapuje go w nowoczesny system modułów ES6. Jednocześnie na samym dole pliku znajduje się stary, ręczny zapis `odoo.define('smart_chat.init_widget', function (require) { ... });`. Odoo przy wczytywaniu takiego pliku może wyrzucić błąd kompilacji aktywów (Assets Bundle Error) lub całkowicie pominąć jeden z modułów.
- **Zalecenie (Fix):** Skoro używamy `/** @odoo-module **/`, cały kod powinien korzystać ze standardu ES6. Rejestrację widgetu należy wykonać za pomocą `import { registry } from "@web/core/registry";` albo całkowicie przenieść mountowanie do osobnego pliku nie-odoo-module (jeśli to wstrzyknięcie czystego HTML).

### 2. 🔴 MAJOR: Użycie `require('web.rpc')` w bloku `try/catch` (ES6 Scope)
- **Problem:** W module kompilowanym przez `@odoo-module`, instrukcja `require` może działać nieprzewidywalnie (zależnie od tego jak transpiler zmapuje zmienne). W nowoczesnym Odoo używamy `import rpc from 'web.rpc';` na samej górze pliku, a nie dynamicznego `require()` w środku funkcji.
- **Zalecenie (Fix):** Przenieść to do importów na górze: `import rpc from "web.rpc";` (lub z `@web/core/network/rpc` w zależności od precyzyjnej wersji silnika, zazwyczaj w legacy-compatibile `@odoo-module` alias `web.rpc` działa poprawnie z importem domyślnym).

---

## 🛠️ Werdykt QA
**BRAMKA NIEZALICZONA (FAILED).**

Poprzedni Hotfix załatał CSRF i blokadę UI, ale zostawił dług techniczny w postaci niepoprawnej składni systemu ładowania modułów JS. Aby Czat faktycznie odpalił się w przeglądarce bez sypania czerwonymi błędami w konsoli Chrome, musimy ostatecznie ustandaryzować architekturę `chat_widget.js`.

Jeśli napiszesz `/dev go`, natychmiast poprawię strukturę importów i wywalę zduplikowany `odoo.define` z pliku ES6!
