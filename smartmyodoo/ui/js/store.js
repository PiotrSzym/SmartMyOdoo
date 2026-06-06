/**
 * Globalny Store dla aplikacji SmartMyOdoo (Vanilla JS Micro-SPA)
 * Odpowiada za utrzymanie stanu (aktywny workspace, aktywna zakładka)
 * oraz powiadamianie komponentów o zmianach (Wzorzec Observer).
 */

class Store {
    constructor() {
        this.state = {
            workspaceId: 'default', // Domyślna przestrzeń robocza
            activeTab: 'vault',  // Domyślna zakładka
            authToken: '',
            isAuthenticated: false
        };
        this.listeners = [];
        console.log('[Store] Zainicjalizowano z domyślnym stanem:', this.state);
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
