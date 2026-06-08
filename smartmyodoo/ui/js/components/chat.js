// js/components/chat.js
// Komponent Czatu AI — pełny interfejs konwersacji z Agentem Swarm

class ChatPanel {
    constructor() {
        this.container = document.getElementById('chat-screen');
        this.messages = [];
        this.sessions = [];
        this.isWaiting = false;
        this.sessionId = `hub-${Date.now()}`;

        // Subskrypcja zmian workspace — czyścimy czat przy przełączeniu
        AppStore.subscribe((newState, oldState) => {
            if (newState.workspaceId !== oldState.workspaceId) {
                this.messages = [];
                this.sessionId = `hub-${Date.now()}`;
                this.loadSessions();
                this.render();
            }
            if (newState.activeTab === 'chat' && oldState.activeTab !== 'chat') {
                // Przy każdym wejściu na zakładkę — załaduj sesje z serwera
                this.loadSessions();
                setTimeout(() => this.scrollToBottom(), 50);
            }
            if (newState.isAuthenticated && !oldState.isAuthenticated) {
                const wsName = this.getWorkspaceName();
                this.addMessage('agent', `Witaj w panelu SmartMyOdoo HUB! 🔒 Połączenie zabezpieczone. Aktywna przestrzeń: ${wsName}. W czym mogę pomóc?`);
            }
        });

        this.render();
    }

    async loadSessions() {
        try {
            const token = window.AppStore.getState().authToken;
            const wsId = window.AppStore.getState().workspaceId;
            const res = await fetch(`/api/chat/sessions?workspace_id=${wsId}&limit=10`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (res.ok) {
                this.sessions = await res.json();
                this.render();
            }
        } catch (e) {
            console.warn('[Chat] Błąd pobierania sesji:', e);
        }
    }

    async switchSession(sessionId) {
        try {
            const token = window.AppStore.getState().authToken;
            const res = await fetch(`/api/chat/sessions/${sessionId}/messages?limit=200`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (res.ok) {
                const msgs = await res.json();
                this.sessionId = sessionId;
                // Zamień format bazy na format UI
                this.messages = msgs.reverse().map(m => {
                    const extra = m.metadata_json ? JSON.parse(m.metadata_json) : {};
                    return {
                        role: m.role,
                        text: m.content,
                        timestamp: new Date(m.timestamp).getTime(),
                        ...extra
                    };
                });
                this.render();
            }
        } catch (e) {
            console.warn('[Chat] Błąd wczytywania wiadomości:', e);
        }
    }

    startNewSession() {
        this.sessionId = `hub-${Date.now()}`;
        this.messages = [];
        this.addMessage('agent', `Rozpoczęto nową sesję konwersacji. W czym mogę pomóc?`);
        this.render();
    }

    getWorkspaceName() {
        const id = AppStore.getState().workspaceId;
        if (window.AppSidebar && window.AppSidebar.workspaces) {
            const ws = window.AppSidebar.workspaces.find(w => w.id === id);
            if (ws) return ws.name;
        }
        return id;
    }

    render() {
        if (!this.container) return;

        const workspaceName = this.getWorkspaceName();

        let messagesHtml = '';
        if (this.messages.length === 0) {
            messagesHtml = `
                <div class="flex-1 flex items-center justify-center">
                    <div class="text-center max-w-md">
                        <div class="text-6xl mb-6 opacity-60">🤖</div>
                        <h2 class="text-2xl font-bold text-gradient mb-3">Witaj w SmartMyOdoo</h2>
                        <p class="text-slate-400 text-sm leading-relaxed">
                            Jestem Twoim Asystentem AI. Mogę zarządzać danymi w Odoo,
                            generować kod, tworzyć raporty i odpowiadać na pytania.
                            Napisz cokolwiek, aby rozpocząć.
                        </p>
                        <div class="flex flex-wrap gap-2 justify-center mt-6">
                            <button onclick="window.AppChat.sendQuickMessage('Pokaż listę kontrahentów')" class="text-xs px-3 py-1.5 rounded-full border border-slate-700 text-slate-400 hover:border-indigo-500 hover:text-indigo-300 transition">📋 Pokaż kontrahentów</button>
                            <button onclick="window.AppChat.sendQuickMessage('Napisz kod migracji danych')" class="text-xs px-3 py-1.5 rounded-full border border-slate-700 text-slate-400 hover:border-indigo-500 hover:text-indigo-300 transition">💻 Napisz kod</button>
                            <button onclick="window.AppChat.sendQuickMessage('Jaka jest architektura systemu?')" class="text-xs px-3 py-1.5 rounded-full border border-slate-700 text-slate-400 hover:border-indigo-500 hover:text-indigo-300 transition">🏗️ Architektura</button>
                        </div>
                    </div>
                </div>
            `;
        } else {
            messagesHtml = '<div class="flex-1 overflow-y-auto px-4 py-6 space-y-4" id="chat-messages-list">';
            this.messages.forEach(msg => {
                messagesHtml += this._renderBubble(msg);
            });
            if (this.isWaiting) {
                messagesHtml += this._renderThinking();
            }
            messagesHtml += '</div>';
        }

        let sidebarHtml = `
            <div class="w-64 border-l border-slate-800 bg-slate-900/40 flex flex-col shrink-0">
                <div class="p-4 border-b border-slate-800">
                    <button onclick="window.AppChat.startNewSession()" class="w-full bg-indigo-600 hover:bg-indigo-500 text-white text-sm py-2 rounded-lg transition font-medium">
                        + Nowy Czat
                    </button>
                </div>
                <div class="flex-1 overflow-y-auto p-2 space-y-1">
                    <div class="px-2 py-1 text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Poprzednie Sesje</div>
                    ${this.sessions.map(s => `
                        <button onclick="window.AppChat.switchSession('${s.session_id}')" class="w-full text-left p-3 rounded-lg transition ${s.session_id === this.sessionId ? 'bg-indigo-500/10 border-indigo-500/30' : 'hover:bg-slate-800 border-transparent'} border">
                            <div class="text-xs text-white truncate font-medium mb-1">${this._escapeHtml(s.preview || 'Nowa sesja')}</div>
                            <div class="flex justify-between items-center text-[10px] text-slate-500">
                                <span>${new Date(s.last_activity).toLocaleDateString()}</span>
                                <span>💬 ${s.message_count}</span>
                            </div>
                        </button>
                    `).join('')}
                    ${this.sessions.length === 0 ? '<div class="px-2 text-xs text-slate-600 italic">Brak historii sesji.</div>' : ''}
                </div>
            </div>
        `;

        this.container.innerHTML = `
            <div class="flex-1 flex flex-col min-w-0">
                <!-- Chat Header -->
                <div class="h-16 border-b border-slate-800 bg-slate-900/50 flex items-center px-6 gap-3 shrink-0">
                    <div class="w-9 h-9 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white text-sm font-bold shadow-lg shadow-indigo-500/20">AI</div>
                    <div class="flex-1">
                        <h3 class="text-sm font-semibold text-white">Agent Swarm</h3>
                        <p class="text-xs text-slate-500">Przestrzeń: <span class="text-indigo-400">${workspaceName}</span> | <span class="opacity-50">Sesja: ${this.sessionId.slice(0, 10)}...</span></p>
                    </div>
                    <div class="flex items-center gap-2">
                        <span class="w-2 h-2 rounded-full bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.8)] animate-pulse"></span>
                        <span class="text-xs text-emerald-400">Online</span>
                    </div>
                </div>

                <!-- Messages Area -->
                ${messagesHtml}

                <!-- Input Bar -->
                <div class="shrink-0 border-t border-slate-800 bg-slate-900/60 p-4">
                    <div class="max-w-4xl mx-auto flex flex-col">
                        ${this._renderSkillBadges()}
                        <div class="flex items-center gap-3">
                            <div class="flex-1 relative">
                                <input
                                    type="text"
                                    id="chat-input"
                                    placeholder="Napisz polecenie dla Agenta..."
                                    class="w-full bg-slate-800/80 border border-slate-700 rounded-xl py-3 px-5 pr-12 text-white text-sm placeholder-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/50 transition-all"
                                    ${this.isWaiting ? 'disabled' : ''}
                                    onkeydown="if(event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); window.AppChat.handleSend(); }"
                                >
                                <div class="absolute right-3 top-1/2 -translate-y-1/2 text-slate-600 text-xs">↵</div>
                            </div>
                            <button
                                onclick="window.AppChat.handleSend()"
                                class="w-11 h-11 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 hover:from-indigo-400 hover:to-purple-500 text-white flex items-center justify-center transition-all shadow-lg shadow-indigo-500/25 hover:shadow-indigo-500/40 ${this.isWaiting ? 'opacity-50 cursor-not-allowed' : ''}"
                                ${this.isWaiting ? 'disabled' : ''}
                            >
                                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"></path></svg>
                            </button>
                        </div>
                    </div>
                </div>
            </div>
            ${sidebarHtml}
        `;

        this.scrollToBottom();

        // Focus input po renderze (jeśli zakładka aktywna)
        if (AppStore.getState().activeTab === 'chat') {
            const input = document.getElementById('chat-input');
            if (input && !this.isWaiting) {
                setTimeout(() => input.focus(), 100);
            }
        }
    }

    _renderSkillBadges() {
        if (!window.AppSkills) return '';
        const selected = window.AppSkills.getSelectedSkills();
        if (!selected || selected.length === 0) return '';

        const badgesHtml = selected.map(skill => {
            return `<span class="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full border bg-indigo-500/20 text-indigo-300 border-indigo-500/30 font-medium">${this._escapeHtml(skill)}</span>`;
        }).join('');

        return `
            <div class="mb-2 flex items-center gap-2 overflow-x-auto pb-1 no-scrollbar">
                <span class="text-xs text-slate-500 shrink-0">Wybrane skille:</span>
                ${badgesHtml}
            </div>
        `;
    }

    _renderBubble(msg) {
        const isUser = msg.role === 'user';
        const time = new Date(msg.timestamp).toLocaleTimeString('pl-PL', { hour: '2-digit', minute: '2-digit' });

        // Shadow Mode Proposal Card
        if (!isUser && msg.actionType === 'SHADOW_PROPOSAL' && msg.proposalData) {
            return this._renderProposalCard(msg, time);
        }

        // Badge persony (jeśli agent)
        let personaBadge = '';
        if (!isUser && msg.persona) {
            const personaColors = {
                'Developer': 'bg-blue-500/20 text-blue-300 border-blue-500/30',
                'Database Administrator': 'bg-amber-500/20 text-amber-300 border-amber-500/30',
                'Quality Assurance': 'bg-green-500/20 text-green-300 border-green-500/30',
                'Technical Writer': 'bg-cyan-500/20 text-cyan-300 border-cyan-500/30',
                'Scout / Researcher': 'bg-rose-500/20 text-rose-300 border-rose-500/30',
                'Architect': 'bg-purple-500/20 text-purple-300 border-purple-500/30',
                'Project Manager': 'bg-orange-500/20 text-orange-300 border-orange-500/30',
                'Generic Assistant': 'bg-slate-500/20 text-slate-300 border-slate-500/30',
            };
            const colorClass = personaColors[msg.persona] || personaColors['Generic Assistant'];
            const personaIcons = {
                'Developer': '💻', 'Database Administrator': '🗄️', 'Quality Assurance': '🧪',
                'Technical Writer': '📝', 'Scout / Researcher': '🔍', 'Architect': '🏗️',
                'Project Manager': '📊', 'Generic Assistant': '🤖',
            };
            const icon = personaIcons[msg.persona] || '🤖';
            personaBadge = `<span class="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full border ${colorClass} font-medium mb-1">${icon} ${msg.persona}</span>`;
        }

        if (isUser) {
            return `
                <div class="flex justify-end gap-3">
                    <div class="max-w-[70%]">
                        <div class="bg-indigo-600/30 border border-indigo-500/20 rounded-2xl rounded-tr-sm px-4 py-3 text-sm text-slate-200 leading-relaxed">
                            ${this._escapeHtml(msg.text)}
                        </div>
                        <p class="text-[10px] text-slate-600 text-right mt-1 mr-1">${time}</p>
                    </div>
                    <div class="w-8 h-8 rounded-full bg-indigo-600/40 flex items-center justify-center text-xs text-indigo-300 shrink-0 mt-1">U</div>
                </div>
            `;
        } else {
            return `
                <div class="flex justify-start gap-3">
                    <div class="w-8 h-8 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-xs text-white shrink-0 mt-1 shadow-lg shadow-purple-500/20">AI</div>
                    <div class="max-w-[70%]">
                        ${personaBadge}
                        <div class="bg-slate-800/60 border border-slate-700/50 rounded-2xl rounded-tl-sm px-4 py-3 text-sm text-slate-300 leading-relaxed backdrop-blur-sm">
                            ${this._escapeHtml(msg.text)}
                        </div>
                        <p class="text-[10px] text-slate-600 mt-1 ml-1">${time}</p>
                    </div>
                </div>
            `;
        }
    }

    _renderProposalCard(msg, time) {
        const p = msg.proposalData;
        const statusColors = {
            'pending': 'border-amber-500/40 bg-amber-500/5',
            'approved': 'border-emerald-500/40 bg-emerald-500/10',
            'rejected': 'border-red-500/40 bg-red-500/10',
        };
        const statusClass = statusColors[msg.proposalStatus || 'pending'] || statusColors['pending'];
        const isPending = (msg.proposalStatus || 'pending') === 'pending';

        return `
            <div class="flex justify-start gap-3">
                <div class="w-8 h-8 rounded-full bg-gradient-to-br from-amber-500 to-orange-600 flex items-center justify-center text-xs text-white shrink-0 mt-1 shadow-lg shadow-amber-500/20">🗄️</div>
                <div class="max-w-[80%] w-full">
                    <span class="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full border bg-amber-500/20 text-amber-300 border-amber-500/30 font-medium mb-1">🗄️ Shadow Mode Proposal</span>
                    <div class="glass-card ${statusClass} rounded-2xl rounded-tl-sm px-5 py-4 backdrop-blur-sm">
                        <h4 class="text-sm font-semibold text-white mb-3 flex items-center gap-2">
                            <span class="w-2 h-2 rounded-full ${isPending ? 'bg-amber-400 animate-pulse' : (msg.proposalStatus === 'approved' ? 'bg-emerald-400' : 'bg-red-400')}"></span>
                            Propozycja operacji na Odoo
                        </h4>
                        <div class="grid grid-cols-2 gap-2 text-xs mb-4">
                            <div class="bg-black/20 rounded-lg p-2">
                                <span class="text-slate-500 block">Model</span>
                                <span class="text-indigo-300 font-mono">${this._escapeHtml(p.model)}</span>
                            </div>
                            <div class="bg-black/20 rounded-lg p-2">
                                <span class="text-slate-500 block">Metoda</span>
                                <span class="text-purple-300 font-mono">${this._escapeHtml(p.method)}</span>
                            </div>
                        </div>
                        <div class="bg-black/20 rounded-lg p-2 text-xs mb-4">
                            <span class="text-slate-500 block mb-1">Powód</span>
                            <span class="text-slate-300">${this._escapeHtml(p.text)}</span>
                        </div>
                        ${isPending ? `
                        <div class="flex gap-3">
                            <button onclick="window.AppChat.handleProposalAction('${p.proposal_id}', 'approve')"
                                class="flex-1 bg-emerald-600/30 hover:bg-emerald-600/50 border border-emerald-500/30 text-emerald-300 py-2 rounded-lg text-sm font-medium transition-all hover:shadow-lg hover:shadow-emerald-500/10">
                                ✅ Approve
                            </button>
                            <button onclick="window.AppChat.handleProposalAction('${p.proposal_id}', 'reject')"
                                class="flex-1 bg-red-600/20 hover:bg-red-600/40 border border-red-500/30 text-red-300 py-2 rounded-lg text-sm font-medium transition-all hover:shadow-lg hover:shadow-red-500/10">
                                ❌ Reject
                            </button>
                        </div>
                        ` : `
                        <div class="text-center py-2 text-xs font-semibold uppercase tracking-wider ${msg.proposalStatus === 'approved' ? 'text-emerald-400' : 'text-red-400'}">
                            ${msg.proposalStatus === 'approved' ? '✅ Zatwierdzona' : '❌ Odrzucona'}
                        </div>
                        `}
                    </div>
                    <p class="text-[10px] text-slate-600 mt-1 ml-1">${time}</p>
                </div>
            </div>
        `;
    }

    _renderThinking() {
        return `
            <div class="flex justify-start gap-3">
                <div class="w-8 h-8 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-xs text-white shrink-0 mt-1 shadow-lg shadow-purple-500/20 animate-pulse">AI</div>
                <div class="max-w-[70%]">
                    <div class="bg-slate-800/60 border border-slate-700/50 rounded-2xl rounded-tl-sm px-4 py-3 backdrop-blur-sm">
                        <div class="flex items-center gap-1.5">
                            <div class="w-2 h-2 rounded-full bg-indigo-400 animate-bounce" style="animation-delay: 0ms"></div>
                            <div class="w-2 h-2 rounded-full bg-purple-400 animate-bounce" style="animation-delay: 150ms"></div>
                            <div class="w-2 h-2 rounded-full bg-pink-400 animate-bounce" style="animation-delay: 300ms"></div>
                            <span class="text-xs text-slate-500 ml-2">Agent myśli...</span>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    _escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    scrollToBottom() {
        const list = document.getElementById('chat-messages-list');
        if (list) {
            setTimeout(() => { list.scrollTop = list.scrollHeight; }, 50);
        }
    }

    handleSend() {
        const input = document.getElementById('chat-input');
        if (!input) return;
        const text = input.value.trim();
        if (!text || this.isWaiting) return;

        this.addMessage('user', text);
        input.value = '';
        this.sendToAPI(text);
    }

    sendQuickMessage(text) {
        if (this.isWaiting) return;
        this.addMessage('user', text);
        this.sendToAPI(text);
    }

    addMessage(role, text, extra = {}) {
        this.messages.push({ role, text, timestamp: Date.now(), ...extra });
        this.render();
    }

    async sendToAPI(message) {
        this.isWaiting = true;
        this.render();

        try {
            const token = window.AppStore.getState().authToken;

            // Get selected skills if the panel is initialized
            const selectedSkills = window.AppSkills ? window.AppSkills.getSelectedSkills() : [];
            const reqSelectedSkills = selectedSkills.length > 0 ? selectedSkills : null;

            const res = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                    message: message,
                    user_id: 1,
                    active_model: null,
                    active_id: null,
                    session_id: this.sessionId,
                    workspace_id: window.AppStore.getState().workspaceId,
                    selected_skills: reqSelectedSkills
                })
            });

            if (!res.ok) {
                throw new Error(`HTTP ${res.status}: ${res.statusText}`);
            }

            const data = await res.json();

            // Handle dispatcher feedback
            if (data.selected_skills && window.AppSkills) {
                // We clear and update the skill panel with what the backend actually used
                window.AppSkills.selectedSkills.clear();
                data.selected_skills.forEach(s => window.AppSkills.selectedSkills.add(s));
                window.AppSkills.render();
            }

            this.isWaiting = false;
            this.addMessage('agent', data.reply || 'Brak odpowiedzi.', {
                persona: data.persona || null,
                category: data.category || null,
                actionType: data.action_type || 'CHAT',
                proposalData: data.proposal_data || null,
                proposalStatus: data.proposal_data ? 'pending' : null,
            });

        } catch (err) {
            console.error('[Chat] Błąd API:', err);
            this.isWaiting = false;
            this.addMessage('agent', `⚠️ Błąd połączenia z Agentem: ${err.message}. Upewnij się, że serwer FastAPI działa na porcie 8000.`);
        }
    }

    async handleProposalAction(proposalId, action) {
        try {
            const token = window.AppStore.getState().authToken;
            const res = await fetch(`/api/proposals/${proposalId}/${action}`, {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (!res.ok) throw new Error(`HTTP ${res.status}`);

            // Zaktualizuj status w historii wiadomości
            const msg = this.messages.find(m => m.proposalData && m.proposalData.proposal_id === proposalId);
            if (msg) {
                msg.proposalStatus = action === 'approve' ? 'approved' : 'rejected';
            }
            this.render();
        } catch (err) {
            console.error('[Chat] Błąd akcji propozycji:', err);
        }
    }
}

// Inicjalizacja komponentu po załadowaniu DOM
document.addEventListener('DOMContentLoaded', () => {
    window.AppChat = new ChatPanel();
});
