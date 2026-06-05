# 🕵️‍♂️ QA Review: F6-01 Frontend-Backend Integration

> **Tryb:** /qa | **Data:** 2026-06-05 | **Projekt:** SmartMyOdoo

W ramach przeglądu kodu wygenerowanego w Fazie 6 (połączenie widgetu OWL z API FastAPI), przeprowadzono rygorystyczny audyt bezpieczeństwa (CORS, CSRF), wydajności oraz zgodności ze standardami Odoo.

Oto raport ze zidentyfikowanymi lukami (Anti-Patterns), które należy załatać.

---

## 🚨 Wykryte Luki i Defekty (QA Findings)

### 1. 🔴 MAJOR: Ryzyko błędu CSRF (Odoo Raw Fetch Anti-Pattern)
- **Problem:** W `chat_widget.js` użyto natywnego `fetch('/smart_chat/send', ...)` ze sztucznym budowaniem wrappera `jsonrpc: "2.0"`. W Odoo wtyczki typu `type='json', auth='user'` bez flagi `csrf=False` domyślnie weryfikują token CSRF sesji. Taki request wysłany z przeglądarki ma 90% szans na odbicie błędem **400 Bad Request (Session Expired / Missing CSRF)**.
- **Zalecenie (Fix):** Kod środowiska `web.core` Odoo posiada bezpieczne metody. Należy użyć natywnego `ajax.rpc` (starsze Odoo) lub `this.env.services.rpc` (OWL v2), które automatycznie dokleja tokeny i ciasteczka sesyjne. Ponieważ używamy legacy injecta `odoo.define`, najlepiej zaimportować `web.rpc`.

### 2. 🟠 MINOR/UX: Brak zabezpieczenia przed spamem (Race Condition)
- **Problem:** Kiedy request do FastAPI leci (`await fetch`), input usera pozostaje aktywny. Użytkownik może zniecierpliwiony kliknąć Enter 5 razy, wypuszczając 5 osobnych zapytań do silnika (który może generować odpowiedź LLM przez np. 10 sekund).
- **Zalecenie (Fix):** Wprowadzić zmienną `this.state.isLoading = true` blokującą pole `t-att-disabled="state.isLoading"` na czas trwania obietnicy RPC, zdejmując blokadę w bloku `finally`. Dodać wskaźnik pisania (Typing indicator).

### 3. 🟡 TRIVIAL: Martwe referencje w OWL
- **Problem:** W pliku `chat_widget.xml` do `<input>` dodano `t-ref="chatInput"`, ale w kodzie JS `chat_widget.js` nigdzie nie użyto `useRef("chatInput")`. Polecono z kolei na natywnym `ev.target.value`. To zły zapach kodu (Code Smell).
- **Zalecenie (Fix):** Usunąć `t-ref` z XML.

### 4. 🟡 TRIVIAL: Typowanie Pydantic w `models.py`
- **Problem:** W pliku `swarm/models.py` użyto `args: list` bez wskazania typu generycznego.
- **Zalecenie (Fix):** Zamienić na `args: list[Any]` i zaimportować `Any`.

---

## 🛠️ Plan Naprawczy (Hotfix)

Jako `/dev` poprawisz powyższe błędy.
