// js/components/sidebar.js
// Komponent odpowiedzialny za boczny pasek i listę przestrzeni roboczych (Workspaces)
// HUB-S3: Ładowanie z API + przycisk "+ Nowa Przestrzeń" → modal
// UX-04: Drag & Drop reorder + Smart Delete

class Sidebar {
    constructor() {
        this.container = document.getElementById('sidebar');
        this.workspaces = [];
        this.isLoading = false;
        this._dragSrcId = null;

        // Subskrypcja stanu
        AppStore.subscribe((newState, oldState) => {
            if (newState.workspaceId !== oldState.workspaceId) {
                this.render();
            }
            if (newState.isAuthenticated && !oldState.isAuthenticated) {
                this.loadFromAPI();
            }
        });

        // Załaduj z API (fallback na hardcoded jeśli API niedostępne)
        this.loadFromAPI();
    }

    async loadFromAPI() {
        try {
            const token = window.AppStore.getState().authToken;
            if (!token) return; // Wait for authentication

            this.isLoading = true;
            this.render();

            const headers = { 'Authorization': `Bearer ${token}` };
            const res = await fetch('/api/workspaces', { headers });
            if (res.ok) {
                this.workspaces = await res.json();
            } else {
                throw new Error('API error');
            }
        } catch (e) {
            console.warn('[Sidebar] Fallback na domyślne workspace:', e);
            this.workspaces = [
                { id: 'default', name: 'Domyślna', position: 0 },
                { id: 'dev', name: 'Dev Env', position: 1 },
                { id: 'prod', name: 'Production', position: 2 }
            ];
        } finally {
            this.isLoading = false;
            this.render();
            // UX-08 (T2): badge zadania w czacie zależy od danych workspace (project_name/task_name).
            // Po (prze)ładowaniu listy odśwież czat, by badge pokazał aktualny projekt › zadanie.
            if (window.AppChat) window.AppChat.render();
        }
    }

    async saveOrder() {
        const order = this.workspaces.map(ws => ws.id);
        const token = window.AppStore.getState().authToken;
        try {
            await fetch('/api/workspaces/reorder', {
                method: 'PUT',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ order })
            });
        } catch (e) {
            console.error('[Sidebar] Failed to save order:', e);
        }
    }

    _handleDragStart(e, wsId) {
        this._dragSrcId = wsId;
        e.dataTransfer.effectAllowed = 'move';
        e.dataTransfer.setData('text/plain', wsId);
        requestAnimationFrame(() => {
            const el = e.target.closest('.ws-item');
            if (el) el.classList.add('dragging');
        });
    }

    _handleDragOver(e) {
        e.preventDefault();
        e.dataTransfer.dropEffect = 'move';
        // Clear all indicators
        this.container.querySelectorAll('.ws-item').forEach(el => {
            el.classList.remove('drag-over-top', 'drag-over-bottom');
        });
        const item = e.target.closest('.ws-item');
        if (item && item.dataset.wsId !== this._dragSrcId) {
            const rect = item.getBoundingClientRect();
            const mid = rect.top + rect.height / 2;
            if (e.clientY < mid) {
                item.classList.add('drag-over-top');
            } else {
                item.classList.add('drag-over-bottom');
            }
        }
    }

    _handleDrop(e) {
        e.preventDefault();
        const targetId = e.target.closest('.ws-item')?.dataset.wsId;
        if (!targetId || targetId === this._dragSrcId) return;

        const targetItem = e.target.closest('.ws-item');
        const insertBefore = targetItem.classList.contains('drag-over-top');

        const dragItem = this.workspaces.find(ws => ws.id === this._dragSrcId);
        if (dragItem) {
            const newOrder = this.workspaces.filter(ws => ws.id !== this._dragSrcId);
            const targetIdx = newOrder.findIndex(ws => ws.id === targetId);

            let insertPos = insertBefore ? targetIdx : targetIdx + 1;
            newOrder.splice(insertPos, 0, dragItem);

            // Re-assign position field for each element based on array index
            newOrder.forEach((ws, i) => ws.position = i);
            this.workspaces = newOrder;

            this.saveOrder();
            this.render();
        }
    }

    _handleDragEnd() {
        this._dragSrcId = null;
        this.container.querySelectorAll('.ws-item').forEach(el => {
            el.classList.remove('dragging', 'drag-over-top', 'drag-over-bottom');
        });
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
                <ul class="space-y-2" id="ws-list">
        `;

        if (this.isLoading) {
            for (let i=0; i<3; i++) {
                html += `
                    <li>
                        <div class="w-full px-4 py-2.5 rounded-lg flex items-center gap-3 bg-slate-800/30 animate-pulse">
                            <div class="w-2 h-2 rounded-full bg-slate-600"></div>
                            <div class="h-4 bg-slate-700 rounded w-24"></div>
                        </div>
                    </li>
                `;
            }
        } else {
            this.workspaces.forEach(ws => {
                const isActive = currentState.workspaceId === ws.id;
                const activeClasses = isActive
                    ? 'bg-indigo-600/20 text-indigo-300 border border-indigo-500/30'
                    : 'text-slate-400 hover:bg-slate-800/50 hover:text-slate-200 border border-transparent';

                html += `
                <li class="ws-item" data-ws-id="${ws.id}" draggable="true">
                    <div class="w-full text-left px-4 py-2.5 rounded-lg text-sm transition-all duration-200 flex items-center gap-3 ${activeClasses} group relative">
                        <span class="cursor-grab active:cursor-grabbing text-slate-600 hover:text-slate-400 select-none" title="Przeciągnij">⠿</span>
                        <button
                            onclick="AppStore.setState({ workspaceId: '${ws.id}', activeTab: 'chat' })"
                            class="flex items-center gap-3 flex-1 text-left"
                        >
                            <span class="w-2 h-2 rounded-full ${isActive ? 'bg-indigo-400 shadow-[0_0_8px_rgba(129,140,248,0.8)]' : 'bg-slate-600'}"></span>
                            ${ws.name}
                        </button>
                        <button
                            onclick="event.stopPropagation(); showDeleteWorkspaceModal('${ws.id}', '${ws.name.replace(/'/g, "\\'")}')"
                            class="ws-delete-btn text-slate-600 hover:text-red-400 text-xs transition p-1 rounded hover:bg-red-500/10"
                            title="Usuń przestrzeń"
                        >🗑️</button>
                    </div>
                </li>
            `;
            });
        }

        html += `
                </ul>
            </div>
            <div class="p-4 border-t border-slate-800">
                <button onclick="showWorkspaceModal()" class="w-full flex items-center justify-center gap-2 text-sm text-slate-400 hover:text-indigo-400 transition-colors p-2 rounded hover:bg-white/5 border border-dashed border-slate-700 hover:border-indigo-500/50">
                    <span>+</span> Nowa Przestrzeń
                </button>
            </div>
        `;

        this.container.innerHTML = html;

        // Bind D&D events
        this.container.querySelectorAll('.ws-item').forEach(item => {
            const wsId = item.dataset.wsId;
            item.addEventListener('dragstart', (e) => this._handleDragStart(e, wsId));
            item.addEventListener('dragenter', (e) => e.preventDefault());
            item.addEventListener('dragover', (e) => this._handleDragOver(e));
            item.addEventListener('drop', (e) => this._handleDrop(e));
            item.addEventListener('dragend', (e) => this._handleDragEnd(e));
        });
    }
}

// Inicjalizacja komponentu po załadowaniu DOM
document.addEventListener('DOMContentLoaded', () => {
    window.AppSidebar = new Sidebar();
});
