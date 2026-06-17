// js/components/taskPicker.js
// UX-08 (T3): Wspólny (reużywalny) Task Picker — wyekstrahowany z project.js STAN 3 (DRY).
// Używany przez:
//   - chat.js  (badge „Zmień" w nagłówku czatu),
//   - project.js (lista zadań w zakładce Projekt — deleguje tu zamiast duplikować).
//
// Logika: pobiera zadania dla projektu związanego z aktywnym workspace
// (GET /api/workspaces/{ws}/projects/{projectId}/tasks) i zapisuje wybór
// przez PUT /api/workspaces/{ws}/task_bind (pełny payload — zachowuje project_ref/name).
//
// ADR-006: vanilla-JS, wzorzec Observer/komponentów js/components, zero nowych zależności.

class TaskPicker {
    constructor() {
        this._overlayId = 'task-picker-overlay';
        this._tasks = [];
        this._projectId = null;
        // Callback wywoływany po udanym bindzie (np. odśwież badge/projekt).
        this._onBound = null;
    }

    // ── Public API ───────────────────────────────────────────────────────────

    /**
     * Ładuje zadania dla projektu (reużywane przez project.js zamiast własnej logiki).
     * @param {string|number} projectId
     * @param {Function} renderTarget callback(tasks) renderujący listę (np. renderTaskList z project.js)
     */
    async loadTasks(projectId, renderTarget) {
        const wsId = AppStore.getState().workspaceId;
        const token = AppStore.getState().authToken;
        this._projectId = projectId;

        const res = await fetch(`/api/workspaces/${wsId}/projects/${projectId}/tasks`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        this._tasks = await res.json();
        if (typeof renderTarget === 'function') renderTarget(this._tasks);
        return this._tasks;
    }

    /**
     * Zapisuje wybrane zadanie do workspace (PUT task_bind, pełny payload).
     * Zachowuje istniejące project_ref/project_name (wymagane przez backend).
     * @param {string|number} taskId
     * @param {string} taskName
     */
    async bind(taskId, taskName) {
        const wsId = AppStore.getState().workspaceId;
        const token = AppStore.getState().authToken;

        const workspaces = (window.AppSidebar && window.AppSidebar.workspaces) || [];
        const ws = workspaces.find(w => w.id === wsId) || {};

        const res = await fetch(`/api/workspaces/${wsId}/task_bind`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                project_ref: ws.project_ref || '',
                project_name: ws.project_name || '',
                task_ref: String(taskId),
                task_name: taskName
            })
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);

        // Odśwież SSoT sidebaru (project_name/task_name) zanim odpalimy callbacki.
        if (window.AppSidebar) await window.AppSidebar.loadFromAPI();
        if (typeof this._onBound === 'function') this._onBound();
        // Re-render czatu (badge) jeśli komponent dostępny.
        if (window.AppChat) window.AppChat.render();
        return await res.json();
    }

    /**
     * Otwiera modal wyboru zadania dla aktywnego workspace.
     * @param {Function} [onBound] callback po zapisaniu wyboru
     */
    async open(onBound) {
        this._onBound = onBound || null;

        const wsId = AppStore.getState().workspaceId;
        const workspaces = (window.AppSidebar && window.AppSidebar.workspaces) || [];
        const ws = workspaces.find(w => w.id === wsId);

        if (!ws || !ws.project_ref) {
            // Brak projektu → skieruj użytkownika do zakładki Projekt.
            alert(window.t ? window.t('chat.noProjectBound') : 'Najpierw wybierz projekt w zakładce Projekt.');
            AppStore.setState({ activeTab: 'settings' });
            return;
        }

        this._ensureOverlay();
        this._show();
        this._setListHtml(`<div class="text-center py-6 text-slate-500 animate-pulse">Ładowanie zadań...</div>`);

        try {
            await this.loadTasks(ws.project_ref, (tasks) => this._renderList(tasks));
        } catch (e) {
            this._setListHtml(`<div class="text-center py-6 text-red-400">Błąd ładowania zadań.</div>`);
        }
    }

    close() {
        const el = document.getElementById(this._overlayId);
        if (el) {
            el.classList.add('hidden');
            el.classList.remove('flex');
        }
    }

    /** Wybór z listy → bind → zamknij modal. */
    async select(taskId, taskName) {
        try {
            await this.bind(taskId, taskName);
            this.close();
        } catch (e) {
            console.error('[TaskPicker] Błąd przypisania zadania:', e);
            this._setListHtml(`<div class="text-center py-6 text-red-400">Nie udało się zapisać wyboru.</div>`);
        }
    }

    filter() {
        const input = document.getElementById('task-picker-search');
        this._renderList(this._tasks, input ? input.value : '');
    }

    // ── Internal: DOM ────────────────────────────────────────────────────────

    _ensureOverlay() {
        if (document.getElementById(this._overlayId)) return;
        const title = window.t ? window.t('chat.pickTaskTitle') : 'Wybierz zadanie';
        const div = document.createElement('div');
        div.id = this._overlayId;
        div.className = 'fixed inset-0 bg-black/80 hidden items-center justify-center p-4 z-50';
        div.innerHTML = `
            <div class="glass-card w-full max-w-lg p-6 relative flex flex-col h-[70vh]">
                <button onclick="window.AppTaskPicker.close()" class="absolute top-4 right-4 text-slate-400 hover:text-white">✕</button>
                <h2 class="text-2xl font-bold mb-4 text-gradient">${this._escape(title)}</h2>
                <input type="text" id="task-picker-search" onkeyup="window.AppTaskPicker.filter()"
                    class="bg-slate-900 border border-slate-700 rounded-lg py-2 px-4 text-white mb-4 shrink-0 focus:outline-none focus:border-indigo-500"
                    placeholder="Szukaj zadania...">
                <div id="task-picker-list" class="flex-1 overflow-y-auto space-y-2 pr-2"></div>
            </div>
        `;
        document.body.appendChild(div);

        // XSS-safe delegacja kliknięć zadań: czyta data-* (dataset = zdekodowany string),
        // zamiast onclick z interpolacją nazwy. Podpięte raz (overlay tworzony raz).
        const listEl = document.getElementById('task-picker-list');
        if (listEl) {
            listEl.addEventListener('click', (e) => {
                const btn = e.target.closest('button[data-task-id]');
                if (btn) this.select(btn.dataset.taskId, btn.dataset.taskName || '');
            });
        }
    }

    _show() {
        const el = document.getElementById(this._overlayId);
        if (el) {
            el.classList.remove('hidden');
            el.classList.add('flex');
        }
    }

    _setListHtml(html) {
        const listEl = document.getElementById('task-picker-list');
        if (listEl) listEl.innerHTML = html;
    }

    _renderList(tasks, filterQuery = '') {
        const listEl = document.getElementById('task-picker-list');
        if (!listEl) return;

        if (!tasks || tasks.length === 0) {
            listEl.innerHTML = `<div class="text-center py-6 text-slate-500">${this._escape(window.t ? window.t('project.noTasks') : 'Brak zadań w projekcie.')}</div>`;
            return;
        }

        const query = filterQuery.toLowerCase();
        const filtered = tasks.filter(t => (t.name || '').toLowerCase().includes(query));
        if (filtered.length === 0) {
            listEl.innerHTML = `<div class="text-center py-6 text-slate-500">${this._escape(window.t ? window.t('project.noResults') : 'Brak wyników.')}</div>`;
            return;
        }

        // XSS-safe: NIE interpolujemy nazwy do onclick (breakout z atrybutu na `"`).
        // Klik obsługuje delegacja w _ensureOverlay przez data-* (dataset = zdekodowany string).
        listEl.innerHTML = filtered.map(t => {
            const isAutoLog = (t.name || '').includes('[SmartMyOdoo]');
            const safeName = this._escape(t.name);
            const safeId = this._escape(String(t.id));
            return `
                <button data-task-id="${safeId}" data-task-name="${this._escapeAttr(t.name)}"
                    class="w-full flex justify-between items-center bg-slate-800 hover:bg-slate-700 border border-slate-700 p-3 rounded-lg transition group">
                    <div class="text-left font-medium ${isAutoLog ? 'text-indigo-400' : 'text-white'} group-hover:text-indigo-300 transition flex items-center gap-2">
                        ${isAutoLog ? '🤖' : '📋'} ${safeName}
                    </div>
                    <div class="text-xs text-slate-500">ID: ${safeId}</div>
                </button>
            `;
        }).join('');
    }

    /** XSS-safe escaping (textContent → innerHTML), jak escapeHtml w project.js/chat.js. */
    _escape(s) {
        if (s === undefined || s === null) return '';
        const div = document.createElement('div');
        div.textContent = s;
        return div.innerHTML;
    }

    /** Escape do KONTEKSTU ATRYBUTU (dodatkowo koduje `"`) — bezpieczne `data-*`. */
    _escapeAttr(s) {
        return this._escape(s).replace(/"/g, '&quot;');
    }
}

// Singleton
document.addEventListener('DOMContentLoaded', () => {
    window.AppTaskPicker = new TaskPicker();
});
