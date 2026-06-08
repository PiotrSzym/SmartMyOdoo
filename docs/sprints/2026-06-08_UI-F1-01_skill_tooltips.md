---
sprint_id: "UI-F1-01"
workspace: "SmartMyOdoo"
status: "DONE"
created: 2026-06-08
goal: "Dodanie luksusowych tooltipów (hover) dla 11 skilli w celu poprawy UX i zrozumienia agentów"
prefix: "UI-F1"
complexity: 2
roadmap_ref: "docs/blueprint/tom2-architektura/roadmap.md"
tags: ["ui", "ux", "tooltips", "skills", "frontend"]
parent_sprint: "ARCH-F7-03"
depends_on: ["ARCH-F7-03"]
---

# 🎨 Sprint UI-F1-01 — Tooltipy kompetencji AI (Skille)

> **Architekt:** /arch | **Data:** 2026-06-08
> **Roadmap ref:** `docs/blueprint/tom2-architektura/roadmap.md`
> **Parent Phase:** Faza UX/UI Enhancements

---

## 📊 Audyt Bieżącego Stanu

- Zarejestrowanych skilli: **11** (pełny zadeklarowany skład TeamEngine).
- Backend (`api.py`): Endpoint `GET /api/skills` zwraca krótkie opisy (`desc`), np. "Standard First — konfiguracja", "Magic Tuples (0,0,{})". Brak pola `tooltip` z pełnym wyjaśnieniem.
- Frontend (`skills.js`): Renderuje kafelki z checkbox, ikoną, nazwą i krótkim `desc`. Brak interakcji hover z rozszerzonym opisem.
- Programy (Szybkie Programy): 5 predefiniowanych zestawów skilli (P1–P5). Również bez tooltipów.

---

## ⚠️ Decyzje wymagające zatwierdzenia

### D1: Język tooltipów
**Rekomendacja:** Język polski — spójny z resztą interfejsu SmartMyOdoo.

### D2: Pozycjonowanie tooltipów
**Rekomendacja:** Tooltip pojawia się **nad** kafelkiem (bottom → top), z fallbackiem na dół jeśli brak miejsca. Styl: glassmorphism (`backdrop-blur-md`, `bg-slate-900/90`).

### D3: Tooltipy na Programach (P1–P5)?
**Rekomendacja:** Na razie **nie** — skupiamy się na 11 skillach. Programy mogą dostać tooltipy w osobnym sprincie.

---

## 🧱 Proposed Changes (Zadania)

### FAZA 1: Rozszerzenie API (Backend)

> **📁 Scope:** `smartmyodoo/api.py` → `get_skills()` (linia ~209)

| # | Zadanie | DoD | Status |
|---|---------|-----|--------|
| 1.1 | Dodanie pola `tooltip` do `ui_defaults` — 11 merytorycznych opisów | Każdy skill ma `tooltip` z 2–3 zdaniami wyjaśniającymi rolę, mechanikę i kiedy używać | [x] |
| 1.2 | Dodanie `tooltip` do appendowanego dicta w pętli `for` | `GET /api/skills` zwraca pole `tooltip` w JSON | [x] |
| 1.3 | **BRAMKA:** `curl /api/skills` → każdy obiekt zawiera klucz `tooltip` z niepustym stringiem | ✅ API contract | [x] |

---

### FAZA 2: Implementacja UI (Frontend)

> **📁 Scope:** `smartmyodoo/ui/js/components/skills.js` → `render()` (linia ~56)

| # | Zadanie | DoD | Status |
|---|---------|-----|--------|
| 2.1 | Dodanie klas `relative group` do kontenera `<label>` kafelka skilla | Kontener gotowy na hover | [x] |
| 2.2 | Budowa diva tooltipowego z glassmorphism | `invisible opacity-0 group-hover:visible group-hover:opacity-100 transition-all duration-300 backdrop-blur-md bg-slate-900/90 border border-indigo-500/30 rounded-xl shadow-2xl z-50` | [x] |
| 2.3 | Pozycjonowanie: tooltip nad kafelkiem, `bottom-full mb-2` | Nie nachodzi na inne elementy, prawidłowy z-index | [x] |
| 2.4 | Obsługa pustego `tooltip` (fallback na `desc`) | Brak crash gdy API nie zwróci tooltipa | [x] |
| 2.5 | **BRAMKA:** Hover nad dowolnym skillem → płynne pojawienie się tooltipa | ✅ UX potwierdzone wizualnie | [x] |

---

## 📈 Sprint Metrics

| Metryka | Przed | Cel |
|---------|-------|-----|
| Pole `tooltip` w `/api/skills` | ❌ Brak | ✅ 11 opisów |
| Hover tooltip w UI | ❌ Brak | ✅ Glassmorphism tooltip |
| Zrozumiałość skilli dla użytkownika | ⚠️ Tylko krótkie skróty | ✅ Pełne wyjaśnienia roli i zastosowania |
| Testy regresji | 87 GREEN | 87+ GREEN (bez regresji) |

---

## 🏁 Definition of Done

- [x] `GET /api/skills` → każdy obiekt zawiera `tooltip` z 2–3 zdaniowym opisem
- [x] Hover nad skillem w UI → płynna animacja tooltipa (premium glassmorphism)
- [x] Wszystkie 11 tooltipów wyjaśniają: co robi skill, jakie ma narzędzia, kiedy go używać
- [x] `python -m pytest tests/ -v` → ALL GREEN (brak regresji)
- [x] Sprint zamknięty w YAML frontmatter (`status: DONE`)

---

## 📚 Lekcje Nauczone (Lessons Learned)

1. **CSS Overflow Clipping (Z-Index Pułapka)**:
   - **Obserwacja**: Tooltipy pozycjonowane absolutnie ku górze (`bottom-full`) na pierwszym rzędzie kafelków były ucinane przez nadrzędny kontener `<main id="main-canvas">` posiadający klasę `overflow-auto`. Wysoki `z-index` nie chroni przed przycięciem (clipping) przez scrollowalnego rodzica.
   - **Rozwiązanie**: W gridach znajdujących się na szczycie okna z `overflow`, elementy hover muszą rozwijać się w dół (`top-full mt-2`). Pozwala to na poprawne renderowanie z-indexu wewnątrz kontenera.
2. **TailwindCSS `group` & `group-hover`**:
   - **Wniosek**: Użycie klasy `group` na kontenerze i `group-hover` na tooltipie pozwala na 100% implementację "glassmorphism hover" wyłącznie w CSS. Eliminuje to konieczność bindowania eventów `onMouseEnter`/`onMouseLeave` w Vanilla JS, co zmniejsza ryzyko wycieków pamięci i bugów przy renderowaniu.
3. **Konflikty Nazw Klas**:
   - **Weryfikacja**: Obawiano się, że klasa `group` na kontenerze "Szybkie Programy" zakłóci działanie `group` na skille (z powodu tej samej struktury CSS). Zweryfikowano, że w TailwindCSS modyfikator `group-hover` dotyczy tylko **bezpośredniego przodka** z klasą `group`, więc poszczególne kafelki nie wpływają na siebie nawzajem.
