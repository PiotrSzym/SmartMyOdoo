// js/components/activity.js
// EP-4: Timeline aktywności agenta — feed z AuditLog

class ActivityPanel {
    constructor() {
        this.container = document.getElementById('activity-screen');
        this.entries = [];
        this.isLoading = false;

        AppStore.subscribe((newState, oldState) => {
            if (newState.activeTab === 'activity' && oldState.activeTab !== 'activity') {
                this.loadFromAPI();
            }
            if (newState.workspaceId !== oldState.workspaceId && newState.activeTab === 'activity') {
                this.loadFromAPI();
            }
        });
    }

    async loadFromAPI() {
        this.isLoading = true;
        this.render();

        try {
            const token = window.AppStore.getState().authToken;
            const wsId = window.AppStore.getState().workspaceId;
            const res = await fetch(`/api/audit?workspace_id=${wsId}&limit=50`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (res.ok) {
                this.entries = await res.json();
            }
        } catch (e) {
            console.warn('[Activity] Nie udało się załadować logów:', e);
            this.entries = [];
        } finally {
            this.isLoading = false;
            this.render();
        }
    }

    _getActionIcon(action) {
        if (action.startsWith('TOOL:odoo_search')) return '🔍';
        if (action.startsWith('TOOL:odoo_create')) return '✏️';
        if (action.startsWith('TOOL:odoo_schema')) return '📋';
        if (action.startsWith('TOOL:scaffold')) return '🏗️';
        if (action.startsWith('TOOL:search_knowledge')) return '🧠';
        if (action.startsWith('TOOL:read_odoo_log')) return '📄';
        if (action.startsWith('TOOL:search_odoo_code')) return '🔎';
        if (action.startsWith('TOOL:rollback')) return '⏮️';
        if (action.includes('ERROR')) return '❌';
        if (action.includes('SESSION')) return '💬';
        return '⚡';
    }

    _getActionColor(action) {
        if (action.includes('ERROR')) return 'border-red-500/30 bg-red-500/5';
        if (action.includes('odoo_create') || action.includes('odoo_update')) return 'border-amber-500/30 bg-amber-500/5';
        if (action.includes('rollback')) return 'border-purple-500/30 bg-purple-500/5';
        return 'border-slate-700/50 bg-slate-800/30';
    }

    _formatTime(isoString) {
        if (!isoString) return '';
        const d = new Date(isoString);
        return d.toLocaleString('pl-PL', {
            month: 'short', day: 'numeric',
            hour: '2-digit', minute: '2-digit', second: '2-digit'
        });
    }

    _parseDetails(detailsStr) {
        try {
            return JSON.parse(detailsStr);
        } catch {
            return null;
        }
    }

    render() {
        if (!this.container) return;

        if (this.isLoading) {
            this.container.innerHTML = `
                <div class="w-full max-w-4xl mx-auto">
                    <h1 class="text-4xl font-bold text-gradient mb-6">📋 Aktywność Agenta</h1>
                    <div class="space-y-4">
                        ${[1,2,3,4].map(() => `
                            <div class="glass-card p-4 animate-pulse">
                                <div class="h-4 bg-slate-700 rounded w-3/4 mb-2"></div>
                                <div class="h-3 bg-slate-700/50 rounded w-1/2"></div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
            return;
        }

        let timelineHtml = '';
        if (this.entries.length === 0) {
            timelineHtml = `
                <div class="text-center py-16">
                    <div class="text-5xl mb-4 opacity-50">📋</div>
                    <p class="text-slate-400">Brak aktywności w tym workspace.</p>
                    <p class="text-xs text-slate-600 mt-2">Wywołania narzędzi agenta pojawią się tutaj automatycznie.</p>
                </div>
            `;
        } else {
            timelineHtml = '<div class="relative">';
            // Pionowa linia osi czasu
            timelineHtml += '<div class="absolute left-6 top-0 bottom-0 w-px bg-gradient-to-b from-indigo-500/50 via-purple-500/30 to-transparent"></div>';

            this.entries.forEach(entry => {
                const icon = this._getActionIcon(entry.action);
                const colorClass = this._getActionColor(entry.action);
                const time = this._formatTime(entry.timestamp);
                const details = this._parseDetails(entry.details);

                const toolName = details?.tool || entry.action.split(':')[1] || entry.action;
                const status = details?.status || (entry.action.includes('ERROR') ? 'ERROR' : 'OK');
                const preview = details?.result_preview || '';

                timelineHtml += `
                    <div class="relative pl-14 pb-6 group">
                        <div class="absolute left-4 w-5 h-5 rounded-full ${status === 'ERROR' ? 'bg-red-500/30 border-red-500' : 'bg-indigo-500/20 border-indigo-500'} border flex items-center justify-center text-xs z-10 group-hover:scale-125 transition-transform">
                            ${icon}
                        </div>
                        <div class="glass-card ${colorClass} p-4 rounded-xl hover:border-indigo-500/30 transition-all">
                            <div class="flex justify-between items-start mb-1">
                                <span class="text-sm font-semibold text-white">${this._escapeHtml(toolName)}</span>
                                <span class="text-[10px] text-slate-500">${time}</span>
                            </div>
                            ${status === 'ERROR' ? '<span class="inline-block text-[10px] px-2 py-0.5 rounded-full bg-red-500/20 text-red-300 border border-red-500/30 mb-2">ERROR</span>' : ''}
                            ${preview ? `<p class="text-xs text-slate-400 mt-1 line-clamp-2">${this._escapeHtml(preview)}</p>` : ''}
                        </div>
                    </div>
                `;
            });

            timelineHtml += '</div>';
        }

        this.container.innerHTML = `
            <div class="w-full max-w-4xl mx-auto">
                <div class="flex justify-between items-center mb-6">
                    <h1 class="text-4xl font-bold text-gradient">📋 Aktywność Agenta</h1>
                    <button onclick="window.AppActivity.loadFromAPI()" class="text-sm text-slate-400 hover:text-indigo-400 transition flex items-center gap-2">
                        🔄 Odśwież
                    </button>
                </div>
                ${timelineHtml}
            </div>
        `;
    }

    _escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.AppActivity = new ActivityPanel();
});
