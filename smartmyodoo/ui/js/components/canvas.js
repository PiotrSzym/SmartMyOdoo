// js/components/canvas.js
// Komponent odpowiedzialny za zawartość strefy roboczej (Z3) i nawigację zakładek (Z2)

class Canvas {
    constructor() {
        this.tabVault = document.getElementById('tab-vault');
        this.tabChat = document.getElementById('tab-chat');
        this.tabActivity = document.getElementById('tab-activity');
        this.tabSettings = document.getElementById('tab-settings');
        this.tabSkills = document.getElementById('tab-skills');
        this.tabModels = document.getElementById('tab-models');
        this.tabDocs = document.getElementById('tab-docs');
        this.tabLogs = document.getElementById('tab-logs');

        this.screenVault = document.getElementById('vault-screen');
        this.screenChat = document.getElementById('chat-screen');
        this.screenActivity = document.getElementById('activity-screen');
        this.screenSettings = document.getElementById('settings-screen');
        this.screenSkills = document.getElementById('skills-screen');
        this.screenModels = document.getElementById('models-screen');
        this.screenDocs = document.getElementById('docs-screen');
        this.screenLogs = document.getElementById('logs-screen');

        // Definicja zakładek: { buttonEl, screenEl }
        this.tabs = [
            { btn: this.tabVault, screen: this.screenVault, key: 'vault' },
            { btn: this.tabChat, screen: this.screenChat, key: 'chat' },
            { btn: this.tabActivity, screen: this.screenActivity, key: 'activity' },
            { btn: this.tabSettings, screen: this.screenSettings, key: 'settings' },
            { btn: this.tabSkills, screen: this.screenSkills, key: 'skills' },
            { btn: this.tabModels, screen: this.screenModels, key: 'models' },
            { btn: this.tabDocs, screen: this.screenDocs, key: 'docs' },
            { btn: this.tabLogs, screen: this.screenLogs, key: 'logs' },
        ];

        // Subskrypcja stanu
        AppStore.subscribe((newState, oldState) => {
            if (newState.activeTab !== oldState.activeTab) {
                this.updateTabs(newState.activeTab);
                // K6: ładuj politykę modeli przy wejściu na zakładkę
                if (newState.activeTab === 'models' && typeof loadModelsPolicy === 'function') {
                    loadModelsPolicy();
                }
            }
            if (newState.workspaceId !== oldState.workspaceId) {
                this.handleWorkspaceChange(newState.workspaceId);
            }
        });

        // Wstępne wyrenderowanie stanu
        this.updateTabs(AppStore.getState().activeTab);
    }

    updateTabs(activeTab) {
        const activeClass = 'text-indigo-400 border-b-2 border-indigo-500';
        const inactiveClass = 'text-slate-400 hover:text-slate-200 border-b-2 border-transparent';

        this.tabs.forEach(({ btn, screen, key }) => {
            if (!btn || !screen) return;

            if (key === activeTab) {
                btn.className = `px-4 py-2 text-sm font-medium transition ${activeClass}`;
                screen.classList.remove('hidden');
                screen.classList.add('flex');
            } else {
                btn.className = `px-4 py-2 text-sm font-medium transition ${inactiveClass}`;
                screen.classList.add('hidden');
                screen.classList.remove('flex');
            }
        });
    }

    handleWorkspaceChange(workspaceId) {
        console.log(`[Canvas] Przestrzeń zmieniona na: ${workspaceId}. Przeładowuję sekrety...`);
        if (typeof loadSecrets === 'function') {
            loadSecrets();
        }
    }
}

// Inicjalizacja komponentu po załadowaniu DOM
document.addEventListener('DOMContentLoaded', () => {
    window.AppCanvas = new Canvas();
});
