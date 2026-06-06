# Sprint FIX-UX-04: Naprawa UI (Drag & Drop + Smart Delete)

**Data utworzenia:** 2026-06-06
**Komponent:** SmartMyOdoo Frontend (Vanilla JS + Tailwind CSS)
**Status:** W TRAKCIE (PLANOWANIE ZAKOŃCZONE, OCZEKUJE NA WDROŻENIE)
**Zgłaszający:** QA / Architekt

## 🎯 1. Cel Sprintu
Rozwiązanie zablokowanego przeciągania obszarów roboczych (Drag & Drop) oraz niedziałającego usuwania przestrzeni z poziomu bocznego panelu UI (błąd referencji). Uzupełnienie dokumentacji technicznej i utworzenie śladu E2E w środowisku CI/CD (Playwright).

## 🔍 2. Analiza Problemu (Root Cause Analysis - RCA)

Podczas manualnego audytu i weryfikacji struktury JS, zidentyfikowano następujące, krytyczne luki po stronie frontendu (`index.html` oraz `sidebar.js`):

### 2.1 ReferenceError w logice Smart Delete
*   **Objaw:** Po kliknięciu 🗑️ ("Usuń") nic się nie dzieje, a konsola przeglądarki rzuca `ReferenceError: AppStore is not defined`.
*   **Przyczyna:** Funkcje obsługujące otwieranie modalu usunięcia i wysyłanie formularza w `index.html` (np. `confirmDeleteWorkspace`) wywoływały globalnie zdefiniowany wewnątrz modułu store obiekt `AppStore`. W zależności od załadowania, skrypt poza modułem traci do niego dostęp bez pełnej ścieżki po obiekcie głównym okna.
*   **Rozwiązanie:** Wymuszenie `window.AppStore` jako kanonicznej ścieżki we wszystkich zdarzeniach `onClick` i logice API wewnątrz tagów `<script>`.

### 2.2 D&D - Zepsuta Propagacja (HTML5 Drag & Drop API)
*   **Objaw:** Upuszczany element nie może zakotwiczyć się na nowej pozycji (przeglądarka odrzuca zdarzenie drop w postaci przekreślonego kółka). Dodatkowo zła kolejność generowana po upuszczeniu przy ułożeniu od dołu w górę.
*   **Przyczyna 1 (Przeglądarka):** Standardy bezpieczeństwa HTML5 wymagają wywołania `e.preventDefault()` w zdarzeniu `dragenter` (oprócz `dragover`), by przeglądarka uznała element za legalny "Drop Zone".
*   **Przyczyna 2 (JS Logic):** Skrypt `_handleDrop` w `sidebar.js` używał `findIndex` po wycięciu (`splice`) głównego elementu. Przesuwało to naturalnie index o `-1`, co powodowało błędne mapowanie `targetId` w nowej skróconej tablicy.
*   **Rozwiązanie:**
    1. Dopisać brakujący event listener na `dragenter` z `e.preventDefault()`.
    2. Przepisać procedurę tablicową w taki sposób, aby pracowała na wyizolowanym od filtrowania nowym wektorze tablicy.

### 2.3 Blokada portów podczas testów zewnętrznych E2E
*   **Objaw:** Błąd na CLI `[winerror 10048] tylko jedno użycie każdego adresu gniazda`.
*   **Przyczyna:** Skrypt `Playwright` próbował asynchronicznie podnieść instancję FastAPI na zarezerwowanym już porcie (8000) używanym przez włączonego przez Developera `vault.py`.
*   **Rozwiązanie:** Izolacja warunków sprawdzania dostępności portu w narzędziu testowym w pliku `test_ui_dnd.py` (sprawdzanie ping i ew. restart instancji w ramach tego samego portu, bez nakładania subprocesów).

## 🛠 3. Procedura Naprawcza (Implementation Plan)

### Etap 1: Stabilizacja Testu Playwright E2E
Utworzono plik `tests/test_ui_dnd.py` z testem asynchronicznym weryfikującym błędy na `page.on("console")` dla podanego środowiska na `localhost:8000`. Test posłuży do certyfikacji naprawy (Brak komunikatów "Browser Error / ReferenceError").

### Etap 2: Modyfikacja HTML (`smartmyodoo/ui/index.html`)
Zamiana w całym bloku `<script>`:
```javascript
// Przed zmianą
const token = AppStore.getState().authToken;

// Po zmianie
const token = window.AppStore.getState().authToken;
```
Dotyczy to w szczególności: `showDeleteWorkspaceModal` oraz `confirmDeleteWorkspace`.

### Etap 3: Re-architektura Listy D&D (`smartmyodoo/ui/js/components/sidebar.js`)
Aktualizacja wiązania eventów:
```javascript
item.addEventListener('dragenter', (e) => e.preventDefault());
```
Wyeliminowanie przesunięcia Index Offsetu wewnątrz metody `_handleDrop`:
```javascript
const dragItem = this.workspaces.find(ws => ws.id === this._dragSrcId);
// Tworzymy nową tablicę OPRÓCZ ciągniętego elementu by ustrzec się błędu splice-shift
const newOrder = this.workspaces.filter(ws => ws.id !== this._dragSrcId);
const targetIdx = newOrder.findIndex(ws => ws.id === targetId);

let insertPos = insertBefore ? targetIdx : targetIdx + 1;
newOrder.splice(insertPos, 0, dragItem);
```

## ✅ 4. Znaki Akceptacji (Verification criteria)
1. Manualne utworzenie przestrzeni, zaznaczenie, i przeniesienie elementu w górę oraz dół zmienia jego pozycję na UI i odsyła do API kod statusu 200.
2. Naciśnięcie ikonki kosza wywołuje widok "Smart Delete Modal". Po wybraniu usunięcia, panel odświeża się bez błędów konsoli znikając z widoku na stałe.

***
**Wymagane akcje po przeczytaniu (dla Dewelopera):**
Jeśli akceptujesz założenia, odpalamy procedurę wpisania modyfikacji do kodu!
