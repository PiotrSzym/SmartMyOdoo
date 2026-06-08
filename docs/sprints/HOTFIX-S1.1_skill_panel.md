# 🚀 Sprint: HOTFIX-S1.1 Skill Panel Chat UI Integration

> **Architekt:** /arch | **Tryb:** Sequential
> **Data:** 2026-06-08 | **Bazuje na:** implementation_plan.md (RCA)

---

## 📋 Sekcja A — Business Discovery & Rules

### Cel biznesowy
Użytkownik zgłosił błąd UX (US-003): "panel skili nie działa analiza dalczego nie widac tablivy i ani skili listy zaznaczoneych chceckboxem". Analiza wykazała, że chociaż logika przypisywania skilli przez Dispatchera działa poprawnie (backend) i stan jest aktualizowany (frontend `SkillPanel`), to w widoku samego Czatu brakuje wizualizacji wybranych skilli. Celem tego hotfixa jest dodanie "odznak" (badges) wybranych skilli w widoku Czatu (tuż nad polem wprowadzania wiadomości) oraz powiązanie ich ze stanem `AppSkills`.

### Metryka sukcesu (DoD)
Wybrane skille (zarówno wybrane ręcznie w zakładce "Skille", jak i te wybrane automatycznie przez Dispatchera po wysłaniu wiadomości) są dynamicznie renderowane jako widoczne odznaki w zakładce "Czat", nad polem inputu.

### ⚖️ ZASADY SPRINTU — Podsumowanie dla Użytkownika

#### Zasada 1: SEQUENTIAL GATE (Bramka Sekwencyjna) 🔴
Faza 1 (Dodanie renderowania odznak w UI) musi zostać zakończona i przetestowana przed Fazą 2 (Podłączenie feedbacku Dispatchera).

#### Zasada 2: TDD FIRST / VALIDATION 🟠
Kod nie jest akceptowany, dopóki manualna weryfikacja w przeglądarce nie potwierdzi prawidłowego odświeżania UI.

#### Zasada 3: SCOPE ISOLATION 🔴
Modyfikacje ograniczają się wyłącznie do 2 plików: `ui/js/components/chat.js` oraz `ui/js/components/skills.js`. Brak modyfikacji backendu.

---

## 🧱 Sekcja B — Podział Zadań

### Graf zależności między Fazami

```
┌──────────────────────────────────────┐
│  FAZA 1 (UI - ChatPanel Badges)      │
│  [1.1 renderSkillBadges]             │
│  [1.2 Kontener w DOM]                │
└──────────────┬───────────────────────┘
               │ ✅ BRAMKA: Badges renderują się ze statycznego stanu
               ▼
┌──────────────────────────────────────┐
│  FAZA 2 (Event Wiring)               │
│  [2.1 toggleSkill update]            │
│  [2.2 Dispatcher feedback update]    │
└──────────────────────────────────────┘
```

---

### Sekcja B1 — FAZA 1: UI - ChatPanel Badges

> **Trigger:** `/dev` rozpoczyna kodowanie
> **📁 Scope:** `smartmyodoo/ui/js/components/chat.js`

| # | Zadanie | DoD | Status |
|---|---------|-----|--------|
| 1.1 | Dodaj metodę `renderSkillBadges()` w `chat.js`, która iteruje po `window.AppSkills.getSelectedSkills()` i generuje HTML z odznakami. | Metoda zwraca poprawnego stringa HTML. | [ ] |
| 1.2 | Zmodyfikuj metodę `render()` w `chat.js`, dodając kontener nad polem `<input id="chat-input">` i wstrzykując tam `renderSkillBadges()`. | Puste/pełne badges są widoczne w DOM. | [ ] |
| 1.3 | **BRAMKA:** Manualna weryfikacja DOM w przeglądarce. | ✅ Odznaki renderują się na twardo. | [ ] |

---

### Sekcja B2 — FAZA 2: Event Wiring

> **Trigger:** Faza 1 ✅
> **📁 Scope:** `smartmyodoo/ui/js/components/skills.js`, `smartmyodoo/ui/js/components/chat.js`

| # | Zadanie | DoD | Status |
|---|---------|-----|--------|
| 2.1 | Zmodyfikuj `toggleSkill` i `clearAll` w `skills.js` — po wywołaniu `this.render()`, dodaj wywołanie `if(window.AppChat) window.AppChat.render()`. | Ręczna zmiana checkboxa aktualizuje Czat. | [ ] |
| 2.2 | Zmodyfikuj blok obsługi feedbacku Dispatchera w `chat.js` (po przypisaniu `data.selected_skills`) tak, aby wywoływał przebudowę UI (np. ponowny render panelu). | Automatyczny wybór przez AI odświeża odznaki w Czacie. | [ ] |
| 2.3 | **BRAMKA:** E2E Flow. | ✅ Zmiany automatyczne i ręczne działają. | [ ] |

---

## ✅ Sekcja E — Finalna Weryfikacja

> Wykonuje użytkownik lub `/qa` po zakończeniu wszystkich faz.

| # | Check (Core Pillars) | Komenda | Oczekiwany wynik |
|---|----------------------|---------|------------------|
| V1 | Uruchomienie Serwera | `python -m smartmyodoo.api` | ✅ Serwer działa, UI ładuje się |
| V2 | Weryfikacja Wizualna (Manual) | Kliknij Skille, wróć na Czat | ✅ Wybrane skille widoczne nad inputem |
| V3 | Weryfikacja Dispatchera (Manual) | Wyślij prompt "Napraw błąd" (auto) | ✅ Skille pojawiają się na żywo w czacie |
