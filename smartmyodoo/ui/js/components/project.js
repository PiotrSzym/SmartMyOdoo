// --- project.js ---
// Obsługa dwustanowej zakładki Projekt (Credentials / Task Picker)

document.addEventListener('DOMContentLoaded', () => {
    if (window.AppStore) {
        window.AppStore.subscribe((newState, oldState) => {
            if (newState.activeTab === 'settings' && oldState.activeTab !== 'settings') {
                renderProjectTab();
            }
            if (newState.workspaceId !== oldState.workspaceId && newState.activeTab === 'settings') {
                renderProjectTab();
            }
        });
    }
});

async function renderProjectTab() {
    const wsId = AppStore.getState().workspaceId;
    if (!wsId || wsId === 'default') {
        // Hide both states or show a message
        document.getElementById('project-state-1').classList.add('hidden');
        document.getElementById('project-state-2').classList.add('hidden');
        return;
    }

    // Pobierz informacje o workspace
    const workspaces = AppStore.getState().workspaces || [];
    const ws = workspaces.find(w => w.id === wsId);

    if (ws && ws.project_ref) {
        // STAN 2: Task Picker
        document.getElementById('project-state-1').classList.add('hidden');
        document.getElementById('project-state-1').classList.remove('block');

        document.getElementById('project-state-2').classList.remove('hidden');
        document.getElementById('project-state-2').classList.add('flex');

        document.getElementById('active-project-name').innerText = ws.project_name || `Projekt ID: ${ws.project_ref}`;
        document.getElementById('active-task-name').innerText = ws.task_name || 'Brak domyślnego zadania';

        loadProjectTasks(ws.project_ref);
    } else {
        // STAN 1: Formularz poświadczeń
        document.getElementById('project-state-2').classList.add('hidden');
        document.getElementById('project-state-2').classList.remove('flex');

        document.getElementById('project-state-1').classList.remove('hidden');
        document.getElementById('project-state-1').classList.add('block');

        // Zresetuj formularz
        document.getElementById('project-credentials-form').reset();
        document.getElementById('proj-connect-msg').classList.add('hidden');
    }
}

async function connectProject(event) {
    event.preventDefault();
    const wsId = AppStore.getState().workspaceId;
    const token = AppStore.getState().authToken;

    const url = document.getElementById('proj-url').value;
    const db = document.getElementById('proj-db').value;
    const login = document.getElementById('proj-login').value;
    const password = document.getElementById('proj-password').value;

    const msgEl = document.getElementById('proj-connect-msg');
    msgEl.innerText = "Zapisywanie w sejfie i łączenie...";
    msgEl.className = "text-sm mt-2 text-indigo-400 text-center block";

    try {
        // Zapisz do sejfu
        const secretPayload = {
            value: password,
            metadata: {
                login: login,
                url: url,
                db: db
            }
        };

        const saveRes = await fetch(`/api/secrets/${wsId}_ODOO`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify(secretPayload)
        });

        if (!saveRes.ok) throw new Error("Nie udało się zapisać w sejfie.");

        // Spróbuj pobrać projekty aby zweryfikować połączenie
        const projRes = await fetch(`/api/workspaces/${wsId}/projects/search?query=`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (!projRes.ok) {
            const err = await projRes.json();
            throw new Error(`Błąd Odoo: ${err.detail}`);
        }

        const projects = await projRes.json();
        if (projects.length === 0) {
            throw new Error("Połączono, ale nie znaleziono żadnych projektów w Odoo.");
        }

        // Automatycznie przypisz pierwszy projekt (lub pozwól userowi wybrać w przyszłości)
        // Dla uproszczenia (F7-01) bierzemy pierwszy aktywny projekt
        const project = projects[0];

        // Bind project to workspace (bez tasku na razie)
        await bindProjectToWorkspace(project.id, project.name);

    } catch (e) {
        msgEl.innerText = e.message;
        msgEl.className = "text-sm mt-2 text-red-400 text-center block";
    }
}

async function bindProjectToWorkspace(projectId, projectName) {
    const wsId = AppStore.getState().workspaceId;
    const token = AppStore.getState().authToken;

    try {
        const res = await fetch(`/api/workspaces/${wsId}/task_bind`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                project_ref: String(projectId),
                project_name: projectName,
                task_ref: "",
                task_name: ""
            })
        });

        if (res.ok) {
            // Reload workspaces and re-render
            window.AppSidebar && await window.AppSidebar.loadWorkspaces();
            renderProjectTab();
        }
    } catch (e) {
        console.error(e);
    }
}

async function loadProjectTasks(projectId) {
    const wsId = AppStore.getState().workspaceId;
    const token = AppStore.getState().authToken;
    const listEl = document.getElementById('proj-task-list');

    listEl.innerHTML = '<div class="text-center py-4 text-slate-500 animate-pulse">Ładowanie zadań...</div>';

    try {
        const res = await fetch(`/api/workspaces/${wsId}/projects/${projectId}/tasks`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (res.ok) {
            window._currentProjectTasks = await res.json();
            renderTaskList(window._currentProjectTasks);
        } else {
            listEl.innerHTML = '<div class="text-center py-4 text-red-400">Błąd ładowania zadań.</div>';
        }
    } catch (e) {
        listEl.innerHTML = '<div class="text-center py-4 text-red-400">Błąd połączenia.</div>';
    }
}

function renderTaskList(tasks, filterQuery = '') {
    const listEl = document.getElementById('proj-task-list');

    if (!tasks || tasks.length === 0) {
        listEl.innerHTML = '<div class="text-center py-4 text-slate-500">Brak zadań w projekcie.</div>';
        return;
    }

    const query = filterQuery.toLowerCase();
    const filtered = tasks.filter(t => t.name.toLowerCase().includes(query));

    if (filtered.length === 0) {
        listEl.innerHTML = '<div class="text-center py-4 text-slate-500">Brak wyników.</div>';
        return;
    }

    // Sort tasks: smartmyodoo task first, then others
    filtered.sort((a, b) => {
        if (a.name.includes('[SmartMyOdoo]')) return -1;
        if (b.name.includes('[SmartMyOdoo]')) return 1;
        return 0;
    });

    listEl.innerHTML = filtered.map(t => {
        const isAutoLog = t.name.includes('[SmartMyOdoo]');
        return `
            <button onclick="bindTaskFromPicker('${t.id}', '${t.name.replace(/'/g, "\\'")}')" class="w-full flex justify-between items-center bg-slate-800 hover:bg-slate-700 border border-slate-700 p-3 rounded-lg transition group">
                <div class="text-left">
                    <div class="font-medium ${isAutoLog ? 'text-indigo-400' : 'text-white'} group-hover:text-indigo-300 transition flex items-center gap-2">
                        ${isAutoLog ? '🤖' : '📋'} ${t.name}
                    </div>
                </div>
                <div class="text-xs text-slate-500">ID: ${t.id}</div>
            </button>
        `;
    }).join('');
}

function filterProjectTasks() {
    const query = document.getElementById('proj-task-search').value;
    renderTaskList(window._currentProjectTasks || [], query);
}

async function bindTaskFromPicker(taskId, taskName) {
    const wsId = AppStore.getState().workspaceId;
    const token = AppStore.getState().authToken;

    // Z zachowaniem aktualnego projektu
    const workspaces = AppStore.getState().workspaces || [];
    const ws = workspaces.find(w => w.id === wsId);

    try {
        const res = await fetch(`/api/workspaces/${wsId}/task_bind`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                project_ref: ws.project_ref,
                project_name: ws.project_name,
                task_ref: String(taskId),
                task_name: taskName
            })
        });

        if (res.ok) {
            window.AppSidebar && await window.AppSidebar.loadWorkspaces();
            renderProjectTab();
        }
    } catch (e) {
        console.error(e);
    }
}

function resetProjectState() {
    if(confirm("Czy na pewno chcesz odpiąć obecny projekt i zadanie? Wprowadzone hasła zostaną w sejfie, ale musisz wybrać projekt ponownie.")) {
        bindProjectToWorkspace("", ""); // Puste = reset
    }
}
