// --- project.js ---
// Obsługa 3-stanowej zakładki Projekt:
//   Stan 1: Formularz credentials (jeśli brak default_ODOO)
//   Stan 2: Wybór projektu (lista projektów z Odoo)
//   Stan 3: Task Picker + Karta Czasu Pracy

function escapeHtml(s) {
    if (!s) return '';
    const div = document.createElement('div');
    div.textContent = s;
    return div.innerHTML;
}

// Escape do KONTEKSTU ATRYBUTU (dodatkowo koduje `"`) — bezpieczne `data-*`.
function escapeAttr(s) {
    return escapeHtml(s).replace(/"/g, '&quot;');
}

document.addEventListener('DOMContentLoaded', () => {
    if (window.AppStore) {
        window.AppStore.subscribe((newState, oldState) => {
            if (newState.activeTab === 'settings' && oldState.activeTab !== 'settings') {
                renderProjectTab();
            }
            // UX-10 (T2/T4): retry-on-auth + fix przywróconej zakładki (parytet ze sidebar.js:18).
            // Vault (/api/secrets) wcześniej NIE ponawiał po zalogowaniu — render odpalał się
            // tylko na PRZEJŚCIU activeTab. Po reloadzie z activeTab='settings' (UX-08, persystencja)
            // brak zdarzenia przejścia → vault zostawał pusty. Guard `!oldState.isAuthenticated`
            // zapobiega pętli (Sekcja D). Renderujemy TYLKO gdy Skarbiec jest aktywną zakładką.
            if (newState.isAuthenticated && !oldState.isAuthenticated && newState.activeTab === 'settings') {
                renderProjectTab();
            }
            if (newState.workspaceId !== oldState.workspaceId && newState.activeTab === 'settings') {
                renderProjectTab();
            }
            if (newState.lang !== oldState.lang && newState.activeTab === 'settings') {
                renderProjectTab();  // I18N-01c
            }
        });
    }
});

// ── Helpers: State Visibility ────────────────────────────────────────────────

function showState(n) {
    [1, 2, 3].forEach(i => {
        const el = document.getElementById(`project-state-${i}`);
        if (!el) return;
        if (i === n) {
            el.classList.remove('hidden');
            el.classList.add('flex');
        } else {
            el.classList.add('hidden');
            el.classList.remove('flex', 'block');
        }
    });
}

// ── RENDER: Główna logika stanu ──────────────────────────────────────────────

async function renderProjectTab() {
    const wsId = AppStore.getState().workspaceId;
    if (!wsId) {
        showState(1);
        return;
    }

    // Pobierz workspace z Sidebar (SSoT)
    const workspaces = (window.AppSidebar && window.AppSidebar.workspaces) || [];
    const ws = workspaces.find(w => w.id === wsId);

    if (ws && ws.project_ref) {
        // STAN 3: Projekt wybrany → Task Picker + Timesheet
        showState(3);
        document.getElementById('active-project-name').innerText = ws.project_name || `Projekt ID: ${ws.project_ref}`;
        document.getElementById('active-task-name').innerText = ws.task_name || (window.t ? window.t('project.noTask') : 'Brak domyślnego zadania');
        loadProjectTasks(ws.project_ref);
    } else {
        // Sprawdź czy mamy credentials w sejfie (default_ODOO)
        try {
            // UX-10 (T5): authFetch dokłada Bearer z AppStore (DRY).
            const secretsRes = await authFetch(`/api/secrets?workspace_id=${wsId}`);
            if (secretsRes.ok) {
                const secrets = await secretsRes.json();
                // Szukaj default_ODOO lub {wsId}_ODOO
                const hasOdoo = secrets.hasOwnProperty('default_ODOO') || secrets.hasOwnProperty(`${wsId}_ODOO`);
                if (hasOdoo) {
                    // Mamy credentials → STAN 2: Wybór projektu
                    showState(2);
                    loadProjectList();
                    return;
                }
            }
        } catch (e) {
            console.warn('Błąd sprawdzania sejfu:', e);
        }
        // Brak credentials → STAN 1: Formularz
        showState(1);
        const form = document.getElementById('project-credentials-form');
        if (form) form.reset();
        const msg = document.getElementById('proj-connect-msg');
        if (msg) msg.classList.add('hidden');
    }
}

// ── STAN 1: Połączenie z Odoo ────────────────────────────────────────────────

async function connectProject(event) {
    event.preventDefault();
    const wsId = AppStore.getState().workspaceId;

    const url = document.getElementById('proj-url').value;
    const db = document.getElementById('proj-db').value;
    const login = document.getElementById('proj-login').value;
    const password = document.getElementById('proj-password').value;

    const msgEl = document.getElementById('proj-connect-msg');
    msgEl.innerText = "Zapisywanie w sejfie i łączenie...";
    msgEl.className = "text-sm mt-2 text-indigo-400 text-center block";

    try {
        // Zapisz do sejfu jako GLOBALNY klucz (wspólny dla wszystkich workspace'ów)
        const secretPayload = {
            password: password,
            login: login,
            url: url,
            db: db,
            api_key: password,
            workspace_id: "default"
        };

        // UX-10 (T5): authFetch dokłada Bearer; tu dokładamy tylko Content-Type.
        const saveRes = await authFetch(`/api/secrets/default_ODOO`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(secretPayload)
        });

        if (!saveRes.ok) throw new Error("Nie udało się zapisać w sejfie.");

        // Po zapisaniu → pokaż Stan 2 (wybór projektu)
        showState(2);
        loadProjectList();

    } catch (e) {
        msgEl.innerText = e.message;
        msgEl.className = "text-sm mt-2 text-red-400 text-center block";
    }
}

// ── STAN 2: Wybór Projektu ───────────────────────────────────────────────────

async function loadProjectList() {
    const wsId = AppStore.getState().workspaceId;
    const listEl = document.getElementById('proj-project-list');

    if (!listEl) return;
    listEl.innerHTML = '<div class="text-center py-4 text-slate-500 animate-pulse">Ładowanie projektów z Odoo...</div>';

    try {
        // UX-10 (T5): authFetch dokłada Bearer z AppStore (DRY).
        const res = await authFetch(`/api/workspaces/${wsId}/projects/search?query=`);

        if (!res.ok) {
            const err = await res.json();
            listEl.innerHTML = `<div class="text-center py-4 text-red-400">Błąd: ${escapeHtml(err.detail || 'Nieznany błąd')}</div>`;
            return;
        }

        window._currentProjectList = await res.json();
        renderProjectList(window._currentProjectList);
    } catch (e) {
        listEl.innerHTML = `<div class="text-center py-4 text-red-400">${window.t ? window.t('project.errConn') : 'Błąd połączenia z Odoo.'}</div>`;
    }
}

function renderProjectList(projects, filterQuery = '') {
    const listEl = document.getElementById('proj-project-list');
    if (!listEl) return;

    if (!projects || projects.length === 0) {
        listEl.innerHTML = `<div class="text-center py-4 text-slate-500">${window.t ? window.t('project.noProjects') : 'Brak projektów w Odoo.'}</div>`;
        return;
    }

    const query = filterQuery.toLowerCase();
    const filtered = projects.filter(p => p.name.toLowerCase().includes(query));

    if (filtered.length === 0) {
        listEl.innerHTML = `<div class="text-center py-4 text-slate-500">${window.t ? window.t('project.noResults') : 'Brak wyników.'}</div>`;
        return;
    }

    // XSS-safe: data-* + delegacja (dataset = zdekodowany string), bez interpolacji nazwy do onclick.
    listEl.innerHTML = filtered.map(p => {
        const safeName = escapeHtml(p.name);
        const safeId = escapeHtml(String(p.id));
        return `
            <button data-project-id="${safeId}" data-project-name="${escapeAttr(p.name)}" class="w-full flex justify-between items-center bg-slate-800 hover:bg-indigo-900/40 border border-slate-700 hover:border-indigo-500 p-4 rounded-lg transition group">
                <div class="text-left flex items-center gap-3">
                    <span class="text-2xl">📁</span>
                    <div>
                        <div class="font-semibold text-white group-hover:text-indigo-300 transition">${safeName}</div>
                        <div class="text-xs text-slate-500">ID: ${safeId}</div>
                    </div>
                </div>
                <span class="text-indigo-400 opacity-0 group-hover:opacity-100 transition">${window.t ? window.t('project.select') : 'Wybierz →'}</span>
            </button>
        `;
    }).join('');
    listEl.onclick = (e) => {
        const btn = e.target.closest('button[data-project-id]');
        if (btn) selectProject(btn.dataset.projectId, btn.dataset.projectName || '');
    };
}

function filterProjectList() {
    const query = document.getElementById('proj-project-search').value;
    renderProjectList(window._currentProjectList || [], query);
}

async function selectProject(projectId, projectName) {
    await bindProjectToWorkspace(projectId, projectName);
}

// ── STAN 3: Task Picker + Timesheet ──────────────────────────────────────────

async function bindProjectToWorkspace(projectId, projectName) {
    const wsId = AppStore.getState().workspaceId;

    try {
        // UX-10 (T5): authFetch dokłada Bearer; tu dokładamy tylko Content-Type.
        const res = await authFetch(`/api/workspaces/${wsId}/task_bind`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                project_ref: String(projectId),
                project_name: projectName,
                task_ref: "",
                task_name: ""
            })
        });

        if (res.ok) {
            window.AppSidebar && await window.AppSidebar.loadFromAPI();
            renderProjectTab();
        }
    } catch (e) {
        console.error(e);
    }
}

async function loadProjectTasks(projectId) {
    const listEl = document.getElementById('proj-task-list');
    listEl.innerHTML = '<div class="text-center py-4 text-slate-500 animate-pulse">Ładowanie zadań...</div>';

    // UX-08 (T3, DRY): pobranie zadań deleguje do wspólnego TaskPickera (nie duplikujemy fetcha).
    try {
        await window.AppTaskPicker.loadTasks(projectId, (tasks) => {
            window._currentProjectTasks = tasks;
            renderTaskList(tasks);
        });
    } catch (e) {
        listEl.innerHTML = `<div class="text-center py-4 text-red-400">${window.t ? window.t('project.errTasks') : 'Błąd ładowania zadań.'}</div>`;
    }
}

function renderTaskList(tasks, filterQuery = '') {
    const listEl = document.getElementById('proj-task-list');

    if (!tasks || tasks.length === 0) {
        listEl.innerHTML = `<div class="text-center py-4 text-slate-500">${window.t ? window.t('project.noTasks') : 'Brak zadań w projekcie.'}</div>`;
        return;
    }

    const query = filterQuery.toLowerCase();
    const filtered = tasks.filter(t => t.name.toLowerCase().includes(query));

    if (filtered.length === 0) {
        listEl.innerHTML = `<div class="text-center py-4 text-slate-500">${window.t ? window.t('project.noResults') : 'Brak wyników.'}</div>`;
        return;
    }

    filtered.sort((a, b) => {
        if (a.name.includes('[SmartMyOdoo]')) return -1;
        if (b.name.includes('[SmartMyOdoo]')) return 1;
        return 0;
    });

    // XSS-safe: data-* + delegacja (dataset = zdekodowany string), bez interpolacji nazwy do onclick.
    listEl.innerHTML = filtered.map(t => {
        const isAutoLog = t.name.includes('[SmartMyOdoo]');
        const safeName = escapeHtml(t.name);
        const safeId = escapeHtml(String(t.id));
        return `
            <button data-task-id="${safeId}" data-task-name="${escapeAttr(t.name)}" class="w-full flex justify-between items-center bg-slate-800 hover:bg-slate-700 border border-slate-700 p-3 rounded-lg transition group">
                <div class="text-left">
                    <div class="font-medium ${isAutoLog ? 'text-indigo-400' : 'text-white'} group-hover:text-indigo-300 transition flex items-center gap-2">
                        ${isAutoLog ? '🤖' : '📋'} ${safeName}
                    </div>
                </div>
                <div class="text-xs text-slate-500">ID: ${safeId}</div>
            </button>
        `;
    }).join('');
    listEl.onclick = (e) => {
        const btn = e.target.closest('button[data-task-id]');
        if (btn) bindTaskFromPicker(btn.dataset.taskId, btn.dataset.taskName || '');
    };
}

function filterProjectTasks() {
    const query = document.getElementById('proj-task-search').value;
    renderTaskList(window._currentProjectTasks || [], query);
}

async function bindTaskFromPicker(taskId, taskName) {
    // UX-08 (T3, DRY): zapis bindu deleguje do wspólnego TaskPickera.
    // Picker odświeża sidebar (SSoT) i re-renderuje czat (badge); tu dorzucamy re-render zakładki Projekt.
    try {
        await window.AppTaskPicker.bind(taskId, taskName);
        renderProjectTab();
    } catch (e) {
        console.error(e);
    }
}

// ── Timesheet: Wpis czasu pracy ──────────────────────────────────────────────

async function logTimesheetEntry(event) {
    event.preventDefault();
    const wsId = AppStore.getState().workspaceId;

    const workspaces = (window.AppSidebar && window.AppSidebar.workspaces) || [];
    const ws = workspaces.find(w => w.id === wsId);

    if (!ws || !ws.project_ref || !ws.task_ref) {
        alert("Najpierw wybierz projekt i domyślne zadanie!");
        return;
    }

    const hours = parseFloat(document.getElementById('ts-hours').value);
    const description = document.getElementById('ts-description').value;
    const msgEl = document.getElementById('ts-msg');

    msgEl.innerText = "Zapisywanie do Odoo...";
    msgEl.className = "text-sm mt-1 text-emerald-400 text-center block";

    try {
        // UX-10 (T5): authFetch dokłada Bearer; tu dokładamy tylko Content-Type.
        const res = await authFetch(`/api/workspaces/${wsId}/timesheet`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                hours: hours,
                description: description
            })
        });

        if (res.ok) {
            msgEl.innerText = `✅ Zapisano ${hours}h do zadania "${ws.task_name}"`;
            msgEl.className = "text-sm mt-1 text-emerald-400 text-center block";
            document.getElementById('ts-description').value = '';
        } else {
            const err = await res.json();
            msgEl.innerText = `❌ ${err.detail || 'Błąd zapisu'}`;
            msgEl.className = "text-sm mt-1 text-red-400 text-center block";
        }
    } catch (e) {
        msgEl.innerText = "❌ Błąd połączenia";
        msgEl.className = "text-sm mt-1 text-red-400 text-center block";
    }
}

// ── Nawigacja między stanami ─────────────────────────────────────────────────

function goBackToProjectPicker() {
    // Wróć do Stanu 2 (wybór projektu) bez resetowania credentials
    showState(2);
    loadProjectList();
}

function resetProjectState() {
    if(confirm("Czy na pewno chcesz odpiąć obecny projekt i zadanie? Wprowadzone hasła zostaną w sejfie, ale musisz wybrać projekt ponownie.")) {
        bindProjectToWorkspace("", ""); // Puste = reset → pokaże Stan 2
    }
}
