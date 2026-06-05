# TeamEngine Sprint Artifact: MCP-02 (Faza 4: Presidio PII Middleware)

**Sprint ID:** MCP-02
**Track ID:** presidio-pii_20260604
**Data utworzenia:** 2026-06-05
**Typ:** Feature (Security / Privacy)

## A. Zasady Bramkowe (TeamEngine Sequential Gates)

1. **RED/GREEN/REFACTOR** – Żaden kod funkcyjny nie może powstać przed napisaniem testu, który obleje (RED).
2. **Commit Gates** – Każda pod-faza (Zadania x.4) kończy się zatrzymaniem agenta i oczekiwaniem na zielone testy / weryfikację.
3. **Audit Log Isolation** – Brak PII w plikach z logami to warunek konieczny przejścia całego sprintu.

## B. Plan Egzekucji i Checklisty

### B1. Faza 1: Presidio Setup + Custom Recognizers

**Cel:** Instalacja Presidio i rozpoznawanie polskich typów danych PII (NIP, PESEL, Imiona).

| # | Zadanie | DoD (Definition of Done) | Status |
|---|---------|--------------------------|--------|
| 1.1 | Instalacja paczek (`presidio-analyzer`, `presidio-anonymizer`) w zależnościach | Zaktualizowany `requirements.txt` / `pyproject.toml` | [ ] |
| 1.2 | 🔴 RED — Testy dla rozpoznawania PII (NIP, PESEL, polskie imiona) | Plik testowy zawiera failing tests | [ ] |
| 1.3 | 🟢 GREEN — Implementacja `NipRecognizer` oraz `PeselRecognizer` | Custom recognizers napisane, testy przechodzą | [ ] |
| 1.4 | **BRAMKA:** Weryfikacja silnika AnalyzerEngine | ✅ Analizator poprawnie identyfikuje encje z 95%+ pewnością | [ ] |

---

### B2. Faza 2: Anonymization Middleware (Reversible Mapping)

**Cel:** Middleware w FastMCP / serwerze, który w locie anonimizuje PII przed LLM i deanominizuje je z powrotem na oryginały.

| # | Zadanie | DoD | Status |
|---|---------|-----|--------|
| 2.1 | 🔴 RED — Testy cyklu anonymize -> deanonymize (roundtrip) | Failing tests dla cyklu tokenizacji i odwracania | [ ] |
| 2.2 | 🟢 GREEN — Implementacja klasy `PiiMiddleware` (z in-memory mapping) | Roundtrip zachowuje mapę dla aktywnej sesji | [ ] |
| 2.3 | Integracja z MCP (podpięcie przed i po logice narzędzi) | `FastMCP` używa middleware automatycznie dla requestów LLM | [ ] |
| 2.4 | **BRAMKA:** Przełącznik per Workspace | ✅ Można wyłączyć/włączyć filtr z poziomu DB / configu | [ ] |

---

### B3. Faza 3: Integracja i Audyt

**Cel:** Gwarancja, że PII nigdy nie lądują w bazie (np. w logach audytowych czy propozycjach shadow mode).

| # | Zadanie | DoD | Status |
|---|---------|-----|--------|
| 3.1 | Implementacja sanityzacji dla `AuditLog` (logujemy akcję, a nie PII) | `AuditLog` nigdy nie przetrzymuje danych typu `<NIP_1>` czy prawdziwego NIP | [ ] |
| 3.2 | Integracja z testowym pipeline / mockowymi wywołaniami Odoo | Odoo otrzymuje prawdziwe dane, LLM otrzymuje zanonimizowane | [ ] |
| 3.3 | Dokumentacja: jak dodawać nowe Recognizery | Zaktualizowany `README` / dokumentacja | [ ] |
| 3.4 | **BRAMKA:** End-to-End Test (Agent -> MCP -> Odoo) | ✅ `pytest` całego modułu MCP PII przechodzi | [ ] |

---

## C. Status Sprintu

| # | Faza | /dev | /qa | /doc | Status |
|---|--------|:----:|:---:|:----:|:------:|
| 1 | Presidio Setup & Recognizers | ⬜ | ⬜ | ⬜ | 🔵 |
| 2 | Anonymization Middleware | ⬜ | ⬜ | ⬜ | 🔵 |
| 3 | Integracja i Audyt | ⬜ | ⬜ | ⬜ | 🔵 |

**Podsumowanie:** 0/3 ✅ Done | Blokujący: —
