/**
 * Globalny Store dla aplikacji SmartMyOdoo (Vanilla JS Micro-SPA)
 * Odpowiada za utrzymanie stanu (aktywny workspace, aktywna zakładka)
 * oraz powiadamianie komponentów o zmianach (Wzorzec Observer).
 */

// UX-08 (BUG-1): klucz localStorage dla nie-wrażliwego stanu UI.
const STORE_PERSIST_KEY = 'smartmyodoo.ui';
// Tylko te pola są persystowane. authToken/isAuthenticated NIGDY (sekrety zostają w pamięci).
const STORE_PERSIST_FIELDS = ['workspaceId', 'activeTab', 'lang'];

class Store {
    constructor() {
        this.state = {
            workspaceId: 'default', // Domyślna przestrzeń robocza
            activeTab: 'chat',  // Domyślna zakładka
            authToken: '',
            isAuthenticated: false,
            lang: 'pl'  // I18N-01: język interfejsu (pl|en)
        };
        this.listeners = [];

        // UX-08 (BUG-1): odtwórz nie-wrażliwy stan UI z localStorage (workspaceId/activeTab/lang).
        // Reload tworzył nową instancję z domyślnym workspaceId='default' → utrata kontekstu.
        const persisted = this._loadPersisted();
        if (persisted) {
            this.state = { ...this.state, ...persisted };
        }

        console.log('[Store] Zainicjalizowano ze stanem:', this.state);
    }

    /**
     * UX-08: Wczytuje nie-wrażliwy stan UI z localStorage (synchron, fail-soft).
     * Nigdy nie odczytuje sekretów (authToken/isAuthenticated tam nie trafiają).
     * @returns {Object|null} Zapisane pola lub null jeśli brak/błąd.
     */
    _loadPersisted() {
        try {
            const raw = window.localStorage.getItem(STORE_PERSIST_KEY);
            if (!raw) return null;
            const parsed = JSON.parse(raw);
            if (!parsed || typeof parsed !== 'object') return null;
            // Whitelist — ignoruj wszystko spoza dozwolonych pól (obrona przed zatrutym storage).
            const safe = {};
            STORE_PERSIST_FIELDS.forEach(k => {
                if (parsed[k] !== undefined) safe[k] = parsed[k];
            });
            return safe;
        } catch (err) {
            console.warn('[Store] Nie udało się odczytać stanu z localStorage:', err);
            return null;
        }
    }

    /**
     * UX-08: Zapisuje TYLKO nie-wrażliwe pola UI do localStorage.
     */
    _persist() {
        try {
            const toSave = {};
            STORE_PERSIST_FIELDS.forEach(k => {
                if (this.state[k] !== undefined) toSave[k] = this.state[k];
            });
            window.localStorage.setItem(STORE_PERSIST_KEY, JSON.stringify(toSave));
        } catch (err) {
            console.warn('[Store] Nie udało się zapisać stanu do localStorage:', err);
        }
    }

    /**
     * Zwraca aktualny stan
     */
    getState() {
        return this.state;
    }

    /**
     * Aktualizuje stan i powiadamia wszystkich subskrybentów
     * @param {Object} newState Częściowy nowy stan do wplecenia (merge)
     */
    setState(newState) {
        const oldState = { ...this.state };
        this.state = { ...this.state, ...newState };
        // UX-08 (BUG-1): utrwal nie-wrażliwy stan UI, by przetrwał reload strony.
        this._persist();
        console.log('[Store] Stan zaktualizowany:', this.state);
        this.notify(this.state, oldState);
    }

    /**
     * Rejestruje funkcję nasłuchującą na zmiany
     * @param {Function} listener Funkcja wywoływana przy każdej zmianie stanu
     * @returns {Function} Funkcja do odsubskrybowania
     */
    subscribe(listener) {
        this.listeners.push(listener);
        console.log(`[Store] Dodano nowego subskrybenta. Łącznie: ${this.listeners.length}`);

        // Zwraca funkcję pozwalającą na usunięcie subskrypcji
        return () => {
            this.listeners = this.listeners.filter(l => l !== listener);
        };
    }

    /**
     * Wywołuje wszystkich subskrybentów, przekazując im nowy i stary stan
     */
    notify(state, oldState) {
        this.listeners.forEach(listener => {
            try {
                listener(state, oldState);
            } catch (err) {
                console.error('[Store] Błąd w subskrybencie:', err);
            }
        });
    }
}

// Inicjalizacja globalnej instancji (Singleton)
window.AppStore = new Store();
