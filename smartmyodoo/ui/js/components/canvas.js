// js/components/canvas.js
// Komponent odpowiedzialny za zawartość strefy roboczej (Z3) i nawigację zakładek (Z2)

class Canvas {
    constructor() {
        this.tabVault = document.getElementById('tab-vault');
        this.tabSettings = document.getElementById('tab-settings');
        this.screenVault = document.getElementById('vault-screen');
        this.screenSettings = document.getElementById('settings-screen');

        // Subskrypcja stanu
        AppStore.subscribe((newState, oldState) => {
            if (newState.activeTab !== oldState.activeTab) {
                this.updateTabs(newState.activeTab);
            }
            if (newState.workspaceId !== oldState.workspaceId) {
                this.handleWorkspaceChange(newState.workspaceId);
            }
        });

        // Wstępne wyrenderowanie stanu
        this.updateTabs(AppStore.getState().activeTab);
    }

    updateTabs(activeTab) {
        if (!this.tabVault || !this.tabSettings) return;

        // Reset klas
        const activeClass = 'text-indigo-400 border-b-2 border-indigo-500';
        const inactiveClass = 'text-slate-400 hover:text-slate-200 border-b-2 border-transparent';

        // Tab Vault
        if (activeTab === 'vault') {
            this.tabVault.className = `px-4 py-2 text-sm font-medium transition ${activeClass}`;
            this.screenVault.classList.remove('hidden');
            this.screenVault.classList.add('flex');
        } else {
            this.tabVault.className = `px-4 py-2 text-sm font-medium transition ${inactiveClass}`;
            this.screenVault.classList.add('hidden');
            this.screenVault.classList.remove('flex');
        }

        // Tab Settings
        if (activeTab === 'settings') {
            this.tabSettings.className = `px-4 py-2 text-sm font-medium transition ${activeClass}`;
            this.screenSettings.classList.remove('hidden');
            this.screenSettings.classList.add('flex');
        } else {
            this.tabSettings.className = `px-4 py-2 text-sm font-medium transition ${inactiveClass}`;
            this.screenSettings.classList.add('hidden');
            this.screenSettings.classList.remove('flex');
        }
    }

    handleWorkspaceChange(workspaceId) {
        console.log(`[Canvas] Przestrzeń zmieniona na: ${workspaceId}. Przeładowuję sekrety...`);
        // Jeśli Vault API obsługiwało by `?workspace_id=...`, tutaj moglibyśmy to przekazać
        // W obecnej formie wywołujemy globalne loadSecrets, które w przyszłości zintegrujemy z backendem MCP.
        if (typeof loadSecrets === 'function') {
            loadSecrets();
        }
    }
}

// Inicjalizacja komponentu po załadowaniu DOM
document.addEventListener('DOMContentLoaded', () => {
    window.AppCanvas = new Canvas();
});
