// js/components/sidebar.js
// Komponent odpowiedzialny za boczny pasek i listę przestrzeni roboczych (Workspaces)

class Sidebar {
    constructor() {
        this.container = document.getElementById('sidebar');
        // Przykładowe dane przestrzeni - docelowo z API
        this.workspaces = [
            { id: 'default', name: 'Domyślna' },
            { id: 'dev', name: 'Dev Env' },
            { id: 'prod', name: 'Production' }
        ];

        // Subskrypcja stanu
        AppStore.subscribe((newState, oldState) => {
            if (newState.workspaceId !== oldState.workspaceId) {
                this.render();
            }
        });

        this.render();
    }

    render() {
        if (!this.container) return;

        const currentState = AppStore.getState();

        let html = `
            <div class="p-6 border-b border-slate-800">
                <h2 class="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-indigo-400 to-purple-400">SmartMyOdoo Hub</h2>
                <p class="text-xs text-slate-500 mt-1">Multi-Workspace Manager</p>
            </div>
            <div class="p-4 flex-1 overflow-y-auto">
                <h3 class="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-4">Przestrzenie Robocze</h3>
                <ul class="space-y-2">
        `;

        this.workspaces.forEach(ws => {
            const isActive = currentState.workspaceId === ws.id;
            const activeClasses = isActive
                ? 'bg-indigo-600/20 text-indigo-300 border border-indigo-500/30'
                : 'text-slate-400 hover:bg-slate-800/50 hover:text-slate-200 border border-transparent';

            html += `
                <li>
                    <button
                        onclick="AppStore.setState({ workspaceId: '${ws.id}' })"
                        class="w-full text-left px-4 py-2.5 rounded-lg text-sm transition-all duration-200 flex items-center gap-3 ${activeClasses}"
                    >
                        <span class="w-2 h-2 rounded-full ${isActive ? 'bg-indigo-400 shadow-[0_0_8px_rgba(129,140,248,0.8)]' : 'bg-slate-600'}"></span>
                        ${ws.name}
                    </button>
                </li>
            `;
        });

        html += `
                </ul>
            </div>
            <div class="p-4 border-t border-slate-800">
                <button class="w-full flex items-center justify-center gap-2 text-sm text-slate-400 hover:text-indigo-400 transition-colors p-2 rounded hover:bg-white/5 border border-dashed border-slate-700 hover:border-indigo-500/50">
                    <span>+</span> Nowa Przestrzeń
                </button>
            </div>
        `;

        this.container.innerHTML = html;
    }
}

// Inicjalizacja komponentu po załadowaniu DOM
document.addEventListener('DOMContentLoaded', () => {
    window.AppSidebar = new Sidebar();
});
