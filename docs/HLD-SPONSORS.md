# SmartMyOdoo — Przegląd dla Sponsorów

> **Dokument wysokopoziomowy.** Bez szczegółów technicznych — nacisk na **bezpieczeństwo,
> prywatność danych i zaufanie**. Wersja: 2026-06-21 (odpowiada wydaniu `v0.1.0`).

---

## 1. Czym jest SmartMyOdoo

Asystent AI dla użytkowników systemu **Odoo (ERP)**. Pomaga prowadzić pracę nad projektami
i zadaniami: rozmawiasz z agentem AI w naturalnym języku, a on wykonuje czynności w Odoo
(rejestracja czasu pracy, podsumowania, raporty) — **zawsze za Twoją zgodą**.

**Wartość:** oszczędność czasu i mniej ręcznej pracy w ERP, przy zachowaniu **pełnej kontroli
człowieka** i **bezkompromisowego bezpieczeństwa danych**.

---

## 2. Filar projektu: BEZPIECZEŃSTWO I PRYWATNOŚĆ

To nie jest dodatek — to fundament architektury. Cztery zasady, które nas wyróżniają:

### 🔒 Zasada 1 — Wszystko zostaje u Ciebie (Local-Only)
Aplikacja działa **lokalnie**, na Twoim komputerze/serwerze. Żadne hasła, poświadczenia ani
wrażliwe dane **nie są wysyłane do chmury** ani synchronizowane na zewnątrz. Nie ma centralnej
bazy, którą można zhakować zbiorczo — dane każdego użytkownika żyją wyłącznie u niego.

### 🗝️ Zasada 2 — Sejf (Vault): Twoje hasła są zaszyfrowane
Poświadczenia do Odoo (login, hasło) trzymane są w **zaszyfrowanym sejfie**:
- Otwierasz go **hasłem głównym (master)**; na co dzień wracasz krótkim **PIN-em**.
- Szyfrowanie klasy bankowej (**AES** + funkcja wzmacniająca hasło z ~**480 000** przekształceń —
  brutalne łamanie jest niepraktyczne).
- Bez Twojego hasła **nikt** — łącznie z samą aplikacją — nie odczyta zawartości sejfu
  (architektura **Zero-Knowledge**).

### 🤖 Zasada 3 — Sztuczna inteligencja NIE WIDZI Twoich sekretów
To jest kluczowe. Model AI (LLM), który napędza rozmowę, **nigdy nie dostaje Twoich haseł**:
- Hasło do Odoo jest pobierane z sejfu i podawane **bezpośrednio do połączenia z Odoo** —
  z pominięciem AI. Agent operuje na danych, ale **nie zna poświadczeń**.
- Nawet gdyby ktoś próbował „podpytać" AI o hasło (prompt injection) — AI **fizycznie go nie ma**.

### 🎭 Zasada 4 — Dane osobowe są anonimizowane, zanim trafią do AI
Zanim jakikolwiek tekst pójdzie do modelu AI, przechodzi przez **automatyczną anonimizację**:
- Dane osobowe (np. „Jan Kowalski", e-maile, telefony) są zamieniane na zastępniki
  (`<OSOBA_1>`, `<EMAIL_1>`) **przed wysłaniem** do AI.
- Po otrzymaniu odpowiedzi system **przywraca** oryginalne dane lokalnie.
- Efekt: **dostawca AI nigdy nie widzi prawdziwych danych osobowych** Twoich klientów.

---

## 3. Jak to działa (w skrócie)

```
   TY  ──rozmowa──▶  SmartMyOdoo (lokalnie)  ──anonimizacja──▶  AI (model językowy)
   ▲                      │     │                                     │
   │                  🗝️ Sejf  🎭 PII                                 │
   │                  (hasła)  (dane osobowe)                         │
   │                      │                                           │
   └──── ZATWIERDŹ ◀── propozycja akcji ◀── (przywrócenie danych) ◀───┘
                            │
                            ▼ (dopiero po Twojej zgodzie)
                         Odoo (ERP)
```

1. Mówisz, co zrobić.
2. System **anonimizuje dane osobowe** i odpytuje AI (bez haseł, bez PII).
3. AI proponuje akcję → **Ty ją zatwierdzasz** (tryb „Shadow Mode" — nic nie dzieje się
   w Odoo bez akceptacji człowieka).
4. Dopiero po zgodzie system łączy się z Odoo (hasło z sejfu, z pominięciem AI) i wykonuje.

---

## 4. Warstwy ochrony (obrona w głąb)

| Warstwa | Co chroni | Jak |
|---|---|---|
| **Lokalność** | Całość danych | Brak chmury — dane nie opuszczają Twojego środowiska |
| **Sejf (AES, Zero-Knowledge)** | Hasła, poświadczenia | Szyfrowane; odczyt tylko Twoim hasłem |
| **Izolacja sekretów od AI** | Hasła | AI nigdy nie otrzymuje poświadczeń |
| **Anonimizacja PII** | Dane osobowe | Maskowane zanim dotrą do AI; przywracane lokalnie |
| **Shadow Mode (człowiek w pętli)** | Integralność ERP | Każda zmiana w Odoo wymaga akceptacji człowieka |
| **Dziennik audytu** | Rozliczalność | Lokalny zapis kto/co/kiedy |

---

## 5. Zgodność i zaufanie

- **Zgodność z RODO/GDPR by design** — minimalizacja danych, anonimizacja, lokalne
  przechowywanie, automatyczne usuwanie starych danych, prawo do usunięcia.
- **Kontrola człowieka** — AI **proponuje**, człowiek **zatwierdza**. Brak autonomicznych
  zmian na danych produkcyjnych.
- **Brak vendor lock-in danych** — dane są Twoje i u Ciebie.

---

## 6. Dojrzałość (stan na v0.1.0)

| Wymiar | Status |
|---|---|
| Gotowość produkcyjna (użytek lokalny) | **85/100 — gotowe do wdrożenia** |
| Bezpieczeństwo (audyt wewnętrzny) | ✅ zweryfikowane (sejf, izolacja sekretów, anonimizacja) |
| Pakowanie / instalacja | ✅ jednym poleceniem (kontener) |
| Jakość (testy automatyczne + CI) | ✅ pełna automatyzacja, bramki jakości |

---

## 7. Podsumowanie dla Sponsora

SmartMyOdoo daje korzyść z AI w pracy z ERP **bez kompromisu na bezpieczeństwie**:
- **Twoje hasła** są w zaszyfrowanym sejfie — **AI ich nie widzi**.
- **Dane osobowe klientów** są anonimizowane, zanim dotrą do AI — **dostawca AI ich nie widzi**.
- **Nic nie zmienia się w ERP bez zgody człowieka**.
- **Wszystko zostaje lokalnie** — żadnej chmury z Twoimi danymi.

To produkt zbudowany wokół zaufania: AI pomaga, ale **nie ma dostępu do tego, co najcenniejsze**.

---

> *Dokument poglądowy dla sponsorów. Szczegóły techniczne: `docs/blueprint/tom2-architektura/HLD-TECHNICAL.md`.*
