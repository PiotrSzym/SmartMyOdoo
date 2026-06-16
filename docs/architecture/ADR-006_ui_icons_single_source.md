# ADR-006 — Ikony UI z jednego źródła (Lucide)

- **Status:** Accepted
- **Data:** 2026-06-16
- **Kontekst sprintu:** DOC-02 (ikony Lucide) + zgłoszenie „standardowe emoji są brzydkie, weźmy je z jednego miejsca"

## Kontekst
Ikony interfejsu były **rozsiane po trzech miejscach** i niespójne (emoji):
1. backend `api_routers/chat.py` (`ui_defaults` w `/api/skills`) — 11 emoji agentów,
2. frontend `ui/js/components/skills.js` — 5 emoji „Szybkich Programów",
3. frontend `ui/js/components/docs.js` (`AGENTS_I18N`) — ponownie emoji agentów.

Skutki: brak spójności wizualnej, „domyślny" wygląd emoji (różny na OS), duplikacja i ryzyko rozjazdu
(zmiana ikony wymaga edycji w wielu plikach), mieszanie **prezentacji** (ikona) z **danymi** (backend).

## Decyzja
1. **Biblioteka ikon:** **Lucide**, hostowana **lokalnie** (`ui/js/vendor/lucide.min.js`, offline-first — patrz [DOC-02]).
2. **Jedno źródło mapowania:** plik **`ui/js/icons.js`** mapuje **stabilne ID** (skill `SkillName`, program `P1..P5`)
   → nazwa ikony Lucide (`SKILL_ICONS`, `PROGRAM_ICONS`) + helpery `skillIcon()/programIcon()`.
   Zmiana/dodanie ikony = **jedna edycja** w tym pliku.
3. **Rozdział prezentacji od danych:** backend (`/api/skills`) zwraca stabilne `id` + metadane; pole `icon`
   (emoji) pozostaje jedynie jako **fallback** dla nieznanych ID. Front renderuje ikonę z `icons.js`.
4. **Render:** komponenty wstawiają `<i data-lucide="...">` i wołają `lucide.createIcons()` po każdym renderze.

## Konsekwencje
- ✅ Spójny, profesjonalny wygląd; zmiana ikon w jednym miejscu.
- ✅ Brak zależności od CDN (offline); brak mieszania UI z backendem.
- ✅ Łatwa rozbudowa (nowy skill → jeden wpis w `icons.js`).
- ⚠️ `icons.js` musi być załadowany przed komponentami (jest — w `index.html` przed `js/components/*`).
- ⚠️ Nazwy ikon muszą istnieć w wersji Lucide z `vendor/` (nieznana nazwa = brak ikony, nie błąd).

## Zakres wdrożenia
- ✅ Skill Panel (`skills.js`) — agenci + programy renderują z `icons.js`.
- 🔜 (follow-up) `docs.js` AGENTS i backend `ui_defaults` — docelowo też tylko `id`, ikona z `icons.js`.

## Powiązane
- [DOC-02 — ikony Lucide + treść dokumentacji](../sprints/2026-06-16_SPRINT-DOC-02_tresc_i_ikony.md)
- [ADR-005 — Agent Integrations](ADR-005_agent_integrations.md)
