---
sprint_id: "HOTFIX-UI-F1-02"
workspace: "SmartMyOdoo"
status: "PLANNED"
created: 2026-06-08
goal: "Naprawa z-index toolptipów (chowanie się pod inne elementy) oraz znaczne wzbogacenie opisów kompetencji agentów"
prefix: "UI-F1"
complexity: 1
roadmap_ref: "docs/blueprint/tom2-architektura/roadmap.md"
tags: ["ui", "hotfix", "tooltips", "z-index"]
parent_sprint: "UI-F1-01"
depends_on: ["UI-F1-01"]
---

# 🎨 Sprint HOTFIX-UI-F1-02 — Naprawa Z-Index i Rozszerzenie Opisów Skilli

> **Architekt:** /arch | **Data:** 2026-06-08
> **Roadmap ref:** `docs/blueprint/tom2-architektura/roadmap.md`

---

## 📊 Audyt Bieżącego Stanu

- Z-Index: Tooltipy chowają się pod elementami (grid items), które renderują się w DOM później.
- Opisy: Użytkownik wskazał, że są "bardzo ubogie".

## 🧱 Proposed Changes (Zadania)

### FAZA 1: Rozszerzenie API (Backend) - Bogatsze Opisy

> **📁 Scope:** `smartmyodoo/api.py`

| # | Zadanie | DoD | Status |
|---|---------|-----|--------|
| 1.1 | Zmiana zawartości pola `tooltip` w `ui_defaults` na bogaty, min. 3-zdaniowy opis | Każdy skill z 11 posiada bardzo dokładne, wyczerpujące wyjaśnienie swojej roli | [ ] |

### FAZA 2: Implementacja UI (Frontend) - Z-Index Fix

> **📁 Scope:** `smartmyodoo/ui/js/components/skills.js`

| # | Zadanie | DoD | Status |
|---|---------|-----|--------|
| 2.1 | Dodanie klasy `hover:z-50` do `<label>` kafelka skilla | Najechanie na kafelek unosi cały kontener w osi Z | [ ] |
| 2.2 | Optymalizacja szerokości tooltipa pod długi tekst | Poszerzenie `w-64` do np. `w-80` lub `w-96`, poprawa line-height | [ ] |

---

## 🏁 Definition of Done
- [ ] Tooltipy zawsze renderują się NAD innymi kafelkami
- [ ] Opisy są długie, merytoryczne i bogate (wyjaśniają role i narzędzia)
- [ ] Z-index fix działa i nie psuje układu
- [ ] Sprint zamknięty w YAML frontmatter (`status: DONE`)
