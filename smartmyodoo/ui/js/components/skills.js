// js/components/skills.js

class SkillPanel {
    constructor() {
        this.container = document.getElementById('skills-screen');
        this.skills = [];

        this.programs = [
            { id: 'P1', icon: '🔍', name: 'Analiza bazy danych', skills: ['ODOO_BUSINESS_ANALYST', 'ODOO_CRUD', 'ODOO_AUDIT_HISTORY'] },
            { id: 'P2', icon: '💻', name: 'Napisanie modułu', skills: ['ODOO_DEVELOPER', 'ODOO_API_EXPERT', 'ODOO_DEVOPS_GITHUB'] },
            { id: 'P3', icon: '🐛', name: 'Sprawdzenie błędu', skills: ['MAGIC_FIX', 'ODOO_SH_LOGS', 'ODOO_DEVELOPER'] },
            { id: 'P4', icon: '⚙️', name: 'Konfiguracja Odoo', skills: ['ODOO_BUSINESS_ANALYST', 'ODOO_CRUD'] },
            { id: 'P5', icon: '📐', name: 'Best practice', skills: ['SECURITY_AUDIT', 'FINANCIAL_AUDIT', 'ODOO_API_EXPERT'] },
        ];

        this.selectedSkills = new Set();

        if (window.AppStore) {
            window.AppStore.subscribe((newState, oldState) => {
                if (newState.activeTab === 'skills' && oldState.activeTab !== 'skills') {
                    this.loadSkills();
                }
                if (newState.authToken !== oldState.authToken && newState.authToken) {
                    this.loadSkills();
                }
                if (newState.isAuthenticated !== oldState.isAuthenticated && newState.isAuthenticated) {
                    this.loadSkills();
                }
                if (newState.workspaceId !== oldState.workspaceId && newState.activeTab === 'skills') {
                    this.loadSkills();
                }
            });
        }

        this.loadSkills();
    }

    async loadSkills() {
        try {
            const token = window.AppStore ? window.AppStore.getState().authToken : '';
            const res = await fetch('/api/skills', {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (res.ok) {
                this.skills = await res.json();
                console.log('[SkillPanel] Załadowano skille z API:', this.skills.length);
                this.render();
            } else {
                console.error('[SkillPanel] Błąd pobierania skilli:', res.status);
            }
        } catch (err) {
            console.error('[SkillPanel] Fetch error:', err);
        }
    }

    render() {
        if (!this.container) return;

        let programsHtml = this.programs.map(p => `
            <button onclick="window.AppSkills.toggleProgram('${p.id}')" class="flex flex-col items-center gap-2 p-4 glass-card hover:bg-indigo-500/10 border border-slate-700/50 hover:border-indigo-500/50 transition-all rounded-xl group text-center">
                <span class="text-3xl group-hover:scale-110 transition-transform">${p.icon}</span>
                <span class="text-sm font-semibold text-slate-300 group-hover:text-indigo-300">${p.name}</span>
            </button>
        `).join('');

        let skillsHtml = this.skills.map(s => {
            const isChecked = this.selectedSkills.has(s.id);
            const badgeReadOnly = s.read_only ? `<span class="text-[9px] px-1.5 py-0.5 rounded-md bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 uppercase tracking-wider font-bold">Read-Only</span>` : '';
            const badgeShadow = s.shadow ? `<span class="text-[9px] px-1.5 py-0.5 rounded-md bg-amber-500/20 text-amber-400 border border-amber-500/30 uppercase tracking-wider font-bold">Shadow</span>` : '';

            return `
            <label class="relative group flex items-start gap-3 p-4 glass-card border ${isChecked ? 'border-indigo-500 bg-indigo-500/10' : 'border-slate-700/50 hover:bg-slate-800/50'} cursor-pointer transition-all rounded-xl">

                <!-- Tooltip -->
                <div class="absolute top-full left-1/2 -translate-x-1/2 mt-2 w-64 p-3 rounded-xl shadow-[0_10px_40px_-10px_rgba(0,0,0,0.5)] z-50 invisible opacity-0 group-hover:visible group-hover:opacity-100 transition-all duration-300 backdrop-blur-md bg-slate-900/95 border border-indigo-500/40 text-sm pointer-events-none">
                    <div class="flex items-center gap-2 mb-1.5 border-b border-slate-700/50 pb-1.5">
                        <span class="text-base">${s.icon}</span>
                        <span class="font-bold text-indigo-300">${s.name}</span>
                    </div>
                    <p class="text-xs leading-relaxed text-slate-300">${s.tooltip || s.desc}</p>

                    <!-- Tooltip Arrow (pointing up) -->
                    <div class="absolute -top-1.5 left-1/2 -translate-x-1/2 w-3 h-3 bg-slate-900 border-t border-l border-indigo-500/40 rotate-45"></div>
                </div>

                <div class="pt-0.5">
                    <input type="checkbox" value="${s.id}" ${isChecked ? 'checked' : ''} onchange="window.AppSkills.toggleSkill('${s.id}')" class="w-4 h-4 rounded border-slate-600 text-indigo-500 focus:ring-indigo-500 bg-slate-900 mt-1 cursor-pointer">
                </div>
                <div class="flex-1">
                    <div class="flex items-center gap-2 mb-1">
                        <span class="text-lg">${s.icon}</span>
                        <span class="font-semibold text-white text-sm">${s.name}</span>
                    </div>
                    <p class="text-xs text-slate-400 mb-2 leading-relaxed">${s.desc}</p>
                    <div class="flex gap-1 flex-wrap">
                        ${badgeReadOnly}
                        ${badgeShadow}
                    </div>
                </div>
            </label>
        `}).join('');

        this.container.innerHTML = `
            <div class="flex justify-between items-center mb-2 mt-4">
                <h1 class="text-3xl font-bold text-gradient">Panel Kompetencji AI</h1>
                <div class="flex gap-3">
                    <button onclick="window.AppSkills.clearAll()" class="px-4 py-2 text-sm text-slate-400 hover:text-red-400 transition">Wyczyść wszystko</button>
                </div>
            </div>

            <div class="mb-8">
                <h2 class="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-4">Szybkie Programy</h2>
                <div class="grid grid-cols-2 md:grid-cols-5 gap-4">
                    ${programsHtml}
                </div>
            </div>

            <div>
                <div class="flex justify-between items-center mb-4">
                    <h2 class="text-sm font-semibold text-slate-400 uppercase tracking-wider">Manualny Wybór Skilli</h2>
                    <span class="text-xs text-indigo-400 font-mono bg-indigo-500/10 px-2 py-1 rounded border border-indigo-500/20">
                        Wybrano: ${this.selectedSkills.size}
                    </span>
                </div>
                <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    ${skillsHtml}
                </div>
            </div>
        `;
    }

    toggleSkill(id) {
        if (this.selectedSkills.has(id)) {
            this.selectedSkills.delete(id);
        } else {
            this.selectedSkills.add(id);
        }
        this.render();
        if (window.AppChat) window.AppChat.render();
    }

    toggleProgram(programId) {
        const prog = this.programs.find(p => p.id === programId);
        if (!prog) return;

        // If all skills in program are already selected, deselect them
        const allSelected = prog.skills.every(s => this.selectedSkills.has(s));

        if (allSelected) {
            prog.skills.forEach(s => this.selectedSkills.delete(s));
        } else {
            prog.skills.forEach(s => this.selectedSkills.add(s));
        }

        this.render();
        if (window.AppChat) window.AppChat.render();
    }

    clearAll() {
        this.selectedSkills.clear();
        this.render();
        if (window.AppChat) window.AppChat.render();
    }

    getSelectedSkills() {
        return Array.from(this.selectedSkills);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.AppSkills = new SkillPanel();
});
