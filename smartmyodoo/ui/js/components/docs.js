// js/components/docs.js
// DOC-02 + I18N-01: Centrum Dokumentacji — dwujęzyczne (PL/EN), sekcje + wyszukiwarka + kompendium.
// Treść per język; ikony sekcji: Lucide. DocsCenter re-renderuje się na zmianę AppStore.lang.

const REPO = "https://github.com/PiotrSzym/SmartMyOdoo/blob/main";

const AGENTS_I18N = {
    pl: [
        ["📊", "Business Analyst", "Standard First", "Analiza biznesowa, architektura procesów i konfiguracja Standard Odoo <b>bez pisania kodu</b>."],
        ["💻", "Developer", "_inherit, no core mod", "Bezpieczne zmiany kodu przez dziedziczenie (<code>_inherit</code>), ORM, zero modyfikacji rdzenia."],
        ["🚀", "DevOps / GitHub", "Staging isolation", "Repozytorium, feature branches, CI/CD, izolowane środowiska staging przed produkcją."],
        ["📋", "SH Logs", "Tracebacki bottom-up", "Odoo.sh i błędy krytyczne — czyta tracebacki od dołu, by znaleźć korzeń błędu."],
        ["🔍", "Audit History", "chatter / mail.message", "Śledzi kto/co/kiedy zmienił przez chatter (<code>mail.message</code>)."],
        ["🗄️", "CRUD", "Magic Tuples", "Manipulacja danymi i relacjami: <code>(0,0,{})</code>, <code>(4,id)</code>, <code>(6,0,[…])</code>."],
        ["📦", "ETL Manager", "Batching 200/req", "Wielkie migracje/importy ze stronicowaniem — omija limity i timeouty."],
        ["💰", "Financial Audit", "Lock Dates", "Księgowość: noty kredytowe, daty blokady, bezpieczeństwo operacji finansowych."],
        ["🔒", "Security Audit", "PII / RODO", "Luki (Record Rules), RODO, szyfrowanie, anonimizacja i pseudonimizacja PII."],
        ["🔌", "API Expert", "XML-RPC / REST", "Integracje zewnętrzne, bezpieczne API Keys, koniec <code>auth=public</code>."],
        ["🪄", "Magic Fix", "Force unlock, kryzys", "Zadania ratunkowe: siłowe odblokowanie locków, uwalnianie cronów, przywracanie środowisk."],
    ],
    en: [
        ["📊", "Business Analyst", "Standard First", "Business analysis, process architecture and Standard Odoo configuration <b>without writing code</b>."],
        ["💻", "Developer", "_inherit, no core mod", "Safe code changes via inheritance (<code>_inherit</code>), ORM, zero core modification."],
        ["🚀", "DevOps / GitHub", "Staging isolation", "Repository, feature branches, CI/CD, isolated staging before production."],
        ["📋", "SH Logs", "Bottom-up tracebacks", "Odoo.sh and critical errors — reads tracebacks bottom-up to find the root cause."],
        ["🔍", "Audit History", "chatter / mail.message", "Tracks who/what/when changed via the chatter (<code>mail.message</code>)."],
        ["🗄️", "CRUD", "Magic Tuples", "Data and relation manipulation: <code>(0,0,{})</code>, <code>(4,id)</code>, <code>(6,0,[…])</code>."],
        ["📦", "ETL Manager", "Batching 200/req", "Large migrations/imports with pagination — avoids limits and timeouts."],
        ["💰", "Financial Audit", "Lock Dates", "Accounting: credit notes, lock dates, safety of financial operations."],
        ["🔒", "Security Audit", "PII / GDPR", "Gaps (Record Rules), GDPR, encryption, anonymization and PII pseudonymization."],
        ["🔌", "API Expert", "XML-RPC / REST", "External integrations, safe API Keys, no more <code>auth=public</code>."],
        ["🪄", "Magic Fix", "Force unlock, crisis", "Rescue tasks: force-unlock locks, free stuck crons, restore environments."],
    ],
};

function _sections(lang) {
    const A = AGENTS_I18N[lang] || AGENTS_I18N.pl;
    const agentsGrid = `<div class="grid grid-cols-1 md:grid-cols-2 gap-2 mt-3">
        ${A.map(([ic, name, tag, desc]) => `
            <div class="bg-black/20 rounded-lg p-3">
                <div class="font-semibold text-white">${ic} ${name} <span class="text-[10px] text-slate-500 font-mono">${tag}</span></div>
                <div class="text-xs text-slate-400 mt-1">${desc}</div>
            </div>`).join("")}
        </div>`;

    const PL = [
        { id: "start", lucide: "rocket", title: "Start", entries: [
            { title: "Czym jest SmartMyOdoo", body: `<p>Middleware AI dla ERP <b>Odoo</b>: rój wyspecjalizowanych agentów z bezpiecznym dostępem do danych — brama FastAPI, swarm (Dispatcher → Executor → Pipeline), serwer MCP, szyfrowany Skarbiec, pseudonimizacja PII i pamięć RAG. Praca w wielu przestrzeniach roboczych powiązanych z zadaniami Odoo/Jira.</p>` },
            { title: "Uruchomienie serwera", body: `<pre>python -m uvicorn smartmyodoo.api:app --host 127.0.0.1 --port 8000</pre><p>Panel: <code>http://127.0.0.1:8000</code> (front serwowany przez backend).</p>` },
            { title: "Logowanie: PIN vs Master", body: `<ul class="list-disc pl-5 space-y-1"><li><b>PIN</b> (4 cyfry) — rola user.</li><li><b>Master Password</b> — rola admin (reset PIN).</li><li>Utrata OBU = bezpowrotna utrata dostępu.</li></ul>` },
            { title: "CLI (klient-serwer)", body: `<p>Interaktywne CLI (Rich) łączy się z backendem przez HTTP/WebSocket — ta sama logika co panel.</p>` },
        ] },
        { id: "features", lucide: "layout-grid", title: "Funkcje", entries: [
            { title: "Multi-Workspace HUB", body: `<p>Wiele projektów naraz; każdy workspace ma konfigurację, poświadczenia i Lessons Learned — wracasz podając tylko PIN.</p>` },
            { title: "Project Hub + Task Picker", body: `<p>Kreator połączeń (Odoo v16 / Jira) z testem połączenia; wyszukiwarka zadań (XML-RPC <code>project.task</code>).</p>` },
            { title: "Auto-Timesheets + raport", body: `<p>Czas pracy → wpis <code>hr.analytic.line</code> z notatką AI przy zamknięciu. Raport miesięczny: godziny + koszty tokenów, eksport CSV.</p>` },
            { title: "AI Session Summary + sync", body: `<p>Raport sesji jako komentarz <code>mail.message</code>; zamknięcie workspace → opcjonalna zmiana statusu zadania (polling 60s).</p>` },
            { title: "Shadow Mode", body: `<p>Operacje na bazie wymagają akceptacji (Proposal). Approve idempotentne + distributed lock — zero podwójnego wykonania.</p>` },
            { title: "Czat + streaming WS", body: `<p>Odpowiedzi strumieniowane przez WebSocket (tokeny, logi narzędzi, stany FSM); badge modelu.</p>` },
            { title: "Fireflies + Audit Trail", body: `<p>Konektor spotkań (webhook). Każde wywołanie narzędzia logowane (z filtrem sekretów) — live timeline w Aktywności.</p>` },
        ] },
        { id: "arch", lucide: "building-2", title: "Architektura", entries: [
            { title: "Brama FastAPI + routery", body: `<p><code>api.py</code> = bootstrap (~95 l.); domeny w <code>api_routers/</code>: auth, secrets, chat, proposals, monitoring, workspaces, models. Deps-module <code>api_deps</code>/<code>chat_deps</code> (brak cyklu).</p>` },
            { title: "Rój agentów (swarm)", body: `<ul class="list-disc pl-5 space-y-1"><li><b>Dispatcher</b> — intencja, persona, model.</li><li><b>SkillExecutor</b> — tool-calling, sandbox, PII, audyt.</li><li><b>Pipeline (FSM)</b> — Auth→Recon→Cognitive→Actuation→Sync (ADP 8 kroków).</li><li><b>MCP</b> — most do Odoo (XML-RPC).</li></ul>` },
            { title: "Pamięć / RAG", body: `<p>LanceDB + SQLite; chunking z overlapem po granicach zdań; tryb zdegradowany zamiast fabrykowania kontekstu.</p>` },
            { title: "Kolejka i workery (Redis)", body: `<p>Niezawodna kolejka (BLMOVE + ack + requeue, TTL) + workery z graceful shutdown.</p>` },
        ] },
        { id: "agents", lucide: "users", title: "Agenci (11)", entries: [
            { title: "Wyspecjalizowane persony", body: `<p>System ma <b>11 agentów</b>. Dispatcher dobiera automatycznie lub wybierasz ręcznie w zakładce Skille. Bariery: read_only / shadow_mode / human_override.</p>${agentsGrid}` },
            { title: "Routing modeli per agent", body: `<p>Każdy agent ma poziom kosztu (CHEAP/STANDARD/PREMIUM). Patrz zakładka Modele.</p>` },
        ] },
        { id: "sec", lucide: "shield", title: "Bezpieczeństwo", entries: [
            { title: "Skarbiec (KEK/Fernet)", body: `<p>Klucz główny (AES-128/Fernet) szyfrowany osobno PIN-em i Master Password (PBKDF2 480k).</p>` },
            { title: "PII (RODO)", body: `<p>Pseudonimizacja przed LLM: <code>Jan Kowalski → &lt;PERSON_1&gt;</code> (odwracalnie, per workspace). Jedna warstwa <code>security/pii/</code>.</p>` },
            { title: "Sandbox fail-closed", body: `<p>Zapisy idą na klon bazy; brak izolacji = blokada zapisu, nie zapis na produkcji.</p>` },
            { title: "TokenGovernor + lock", body: `<ul class="list-disc pl-5 space-y-1"><li>Kontrola budżetu LLM (pre-flight).</li><li>Distributed lock (anty-TOCTOU) na approve.</li><li>CORS jawne originy + rate-limit logowania.</li></ul>` },
        ] },
        { id: "vault", lucide: "key-round", title: "Skarbiec & Klucze", entries: [
            { title: "Trzy typy kluczy", body: `<ul class="list-disc pl-5 space-y-1"><li>🔑 llm_provider — klucz API modelu.</li><li>🗄️ odoo_data — Odoo (dane).</li><li>⏱️ odoo_timesheet — Odoo (czas pracy).</li></ul>` },
            { title: "AI bez znajomości haseł", body: `<p>Sekrety wstrzykiwane do środowiska w locie; do LLM idą tylko pseudonimy. Resolver: timesheet → data → legacy.</p>` },
        ] },
        { id: "models", lucide: "sliders-horizontal", title: "Modele AI", entries: [
            { title: "Tiery kosztów", body: `<ul class="list-disc pl-5 space-y-1"><li>CHEAP — klasyfikacja.</li><li>STANDARD — dev/CRUD.</li><li>PREMIUM — architektura/audyt.</li></ul><p>Edycja: zakładka Modele (<code>GET/PUT /api/models/policy</code>).</p>` },
            { title: "Odporność i wydajność", body: `<ul class="list-disc pl-5 space-y-1"><li>Retry + fallback + backoff.</li><li>Cache (In-Memory/Redis).</li><li>Degradacja budżetu zamiast blokady.</li></ul>` },
        ] },
        { id: "kb", lucide: "book-open", title: "Kompendium wiedzy", entries: [
            { title: "Odoo: edycje i hosting", body: `<ul class="list-disc pl-5 space-y-1"><li>Community vs Enterprise.</li><li>SaaS / Odoo.sh / On-Premise.</li><li>Wersje 16/17/18/19 — zgodność modułów.</li></ul>` },
            { title: "Pułapki Odoo", body: `<ul class="list-disc pl-5 space-y-1"><li>Nie modyfikuj rdzenia — <code>_inherit</code>.</li><li>Magic Tuples: <code>(0,0,{})</code>, <code>(4,id)</code>, <code>(6,0,[ids])</code>.</li><li>Lock Dates — używaj not kredytowych.</li><li>Batching importu (200/req).</li><li><b>Odoo.sh — nazwa bazy:</b> wpisuj SAM slug (np. <code>myodoo-...-master-6970793</code>), <b>bez</b> etykiety <code>[branch/version]</code> — inaczej <code>database "... [production/16.0]" does not exist</code>.</li></ul>` },
            { title: "FAQ", body: `<ul class="list-disc pl-5 space-y-1"><li><b>AI widzi hasła?</b> Nie.</li><li><b>Port?</b> <code>:8000</code>.</li><li><b>Brak klucza?</b> tryb heurystyczny.</li><li><a class="text-indigo-400 underline" target="_blank" href="${REPO}/docs/README.md">repo docs/</a></li></ul>` },
        ] },
    ];

    const EN = [
        { id: "start", lucide: "rocket", title: "Start", entries: [
            { title: "What is SmartMyOdoo", body: `<p>AI middleware for the <b>Odoo</b> ERP: a swarm of specialized agents with secure data access — FastAPI gateway, swarm (Dispatcher → Executor → Pipeline), MCP server, encrypted Vault, PII pseudonymization and RAG memory. Work across multiple workspaces bound to Odoo/Jira tasks.</p>` },
            { title: "Run the server", body: `<pre>python -m uvicorn smartmyodoo.api:app --host 127.0.0.1 --port 8000</pre><p>Panel: <code>http://127.0.0.1:8000</code> (frontend served by the backend).</p>` },
            { title: "Login: PIN vs Master", body: `<ul class="list-disc pl-5 space-y-1"><li><b>PIN</b> (4 digits) — user role.</li><li><b>Master Password</b> — admin role (reset PIN).</li><li>Losing BOTH = permanent loss of access.</li></ul>` },
            { title: "CLI (client-server)", body: `<p>Interactive CLI (Rich) connects to the backend over HTTP/WebSocket — same logic as the panel.</p>` },
        ] },
        { id: "features", lucide: "layout-grid", title: "Features", entries: [
            { title: "Multi-Workspace HUB", body: `<p>Many projects at once; each workspace keeps config, credentials and Lessons Learned — resume with just a PIN.</p>` },
            { title: "Project Hub + Task Picker", body: `<p>Connection wizard (Odoo v16 / Jira) with a connection test; task search (XML-RPC <code>project.task</code>).</p>` },
            { title: "Auto-Timesheets + report", body: `<p>Worked time → <code>hr.analytic.line</code> entry with an AI note on close. Monthly report: hours + token costs, CSV export.</p>` },
            { title: "AI Session Summary + sync", body: `<p>Session report as a <code>mail.message</code> comment; closing a workspace → optional task status change (60s polling).</p>` },
            { title: "Shadow Mode", body: `<p>DB operations require approval (Proposal). Approve is idempotent + distributed lock — no double execution.</p>` },
            { title: "Chat + WS streaming", body: `<p>Replies streamed over WebSocket (tokens, tool logs, FSM states); model badge.</p>` },
            { title: "Fireflies + Audit Trail", body: `<p>Meeting connector (webhook). Every tool call is logged (with secret filter) — live timeline in Activity.</p>` },
        ] },
        { id: "arch", lucide: "building-2", title: "Architecture", entries: [
            { title: "FastAPI gateway + routers", body: `<p><code>api.py</code> = bootstrap (~95 l.); domains in <code>api_routers/</code>: auth, secrets, chat, proposals, monitoring, workspaces, models. Deps-module <code>api_deps</code>/<code>chat_deps</code> (no import cycle).</p>` },
            { title: "Agent swarm", body: `<ul class="list-disc pl-5 space-y-1"><li><b>Dispatcher</b> — intent, persona, model.</li><li><b>SkillExecutor</b> — tool-calling, sandbox, PII, audit.</li><li><b>Pipeline (FSM)</b> — Auth→Recon→Cognitive→Actuation→Sync (ADP 8 steps).</li><li><b>MCP</b> — bridge to Odoo (XML-RPC).</li></ul>` },
            { title: "Memory / RAG", body: `<p>LanceDB + SQLite; chunking with sentence-boundary overlap; degraded mode instead of fabricating context.</p>` },
            { title: "Queue & workers (Redis)", body: `<p>Reliable queue (BLMOVE + ack + requeue, TTL) + workers with graceful shutdown.</p>` },
        ] },
        { id: "agents", lucide: "users", title: "Agents (11)", entries: [
            { title: "Specialized personas", body: `<p>The system has <b>11 agents</b>. The Dispatcher picks one automatically, or you choose manually in the Skills tab. Guards: read_only / shadow_mode / human_override.</p>${agentsGrid}` },
            { title: "Per-agent model routing", body: `<p>Each agent has a cost tier (CHEAP/STANDARD/PREMIUM). See the Models tab.</p>` },
        ] },
        { id: "sec", lucide: "shield", title: "Security", entries: [
            { title: "Vault (KEK/Fernet)", body: `<p>Master key (AES-128/Fernet) encrypted separately by the PIN and the Master Password (PBKDF2 480k).</p>` },
            { title: "PII (GDPR)", body: `<p>Pseudonymization before the LLM: <code>Jan Kowalski → &lt;PERSON_1&gt;</code> (reversible, per workspace). One layer <code>security/pii/</code>.</p>` },
            { title: "Sandbox fail-closed", body: `<p>Writes go to a DB clone; no isolation = write blocked, never written to production.</p>` },
            { title: "TokenGovernor + lock", body: `<ul class="list-disc pl-5 space-y-1"><li>LLM budget control (pre-flight).</li><li>Distributed lock (anti-TOCTOU) on approve.</li><li>Explicit CORS origins + login rate-limit.</li></ul>` },
        ] },
        { id: "vault", lucide: "key-round", title: "Vault & Keys", entries: [
            { title: "Three key types", body: `<ul class="list-disc pl-5 space-y-1"><li>🔑 llm_provider — model API key.</li><li>🗄️ odoo_data — Odoo (data).</li><li>⏱️ odoo_timesheet — Odoo (timesheets).</li></ul>` },
            { title: "AI without knowing passwords", body: `<p>Secrets injected into the runtime on the fly; only pseudonyms reach the LLM. Resolver: timesheet → data → legacy.</p>` },
        ] },
        { id: "models", lucide: "sliders-horizontal", title: "AI Models", entries: [
            { title: "Cost tiers", body: `<ul class="list-disc pl-5 space-y-1"><li>CHEAP — classification.</li><li>STANDARD — dev/CRUD.</li><li>PREMIUM — architecture/audit.</li></ul><p>Edit: Models tab (<code>GET/PUT /api/models/policy</code>).</p>` },
            { title: "Resilience & performance", body: `<ul class="list-disc pl-5 space-y-1"><li>Retry + fallback + backoff.</li><li>Cache (In-Memory/Redis).</li><li>Budget degradation instead of a hard block.</li></ul>` },
        ] },
        { id: "kb", lucide: "book-open", title: "Knowledge base", entries: [
            { title: "Odoo: editions & hosting", body: `<ul class="list-disc pl-5 space-y-1"><li>Community vs Enterprise.</li><li>SaaS / Odoo.sh / On-Premise.</li><li>Versions 16/17/18/19 — module compatibility.</li></ul>` },
            { title: "Odoo pitfalls", body: `<ul class="list-disc pl-5 space-y-1"><li>Don't modify core — use <code>_inherit</code>.</li><li>Magic Tuples: <code>(0,0,{})</code>, <code>(4,id)</code>, <code>(6,0,[ids])</code>.</li><li>Lock Dates — use credit notes.</li><li>Import batching (200/req).</li><li><b>Odoo.sh — DB name:</b> enter the bare slug (e.g. <code>myodoo-...-master-6970793</code>), <b>without</b> the <code>[branch/version]</code> label — otherwise <code>database "... [production/16.0]" does not exist</code>.</li></ul>` },
            { title: "FAQ", body: `<ul class="list-disc pl-5 space-y-1"><li><b>Does AI see passwords?</b> No.</li><li><b>Port?</b> <code>:8000</code>.</li><li><b>No key?</b> heuristic mode.</li><li><a class="text-indigo-400 underline" target="_blank" href="${REPO}/docs/README.md">repo docs/</a></li></ul>` },
        ] },
    ];

    return lang === "en" ? EN : PL;
}

class DocsCenter {
    constructor() {
        this.screen = document.getElementById("docs-screen");
        this.active = "start";
        this.query = "";
        if (this.screen) this.render();
    }

    _lang() {
        try {
            return (window.AppStore && AppStore.getState().lang) || "pl";
        } catch (_) {
            return "pl";
        }
    }

    _tt(key, fallback) {
        return window.t ? window.t(key) : fallback;
    }

    _match(entry, q) {
        return (entry.title + " " + entry.body).toLowerCase().includes(q);
    }

    render() {
        const sections = _sections(this._lang());
        const q = this.query.trim().toLowerCase();
        if (!sections.find((s) => s.id === this.active)) this.active = sections[0].id;

        const sidebar = sections.map(
            (s) => `
            <button data-doc-section="${s.id}"
                class="w-full text-left px-3 py-2 rounded-lg text-sm transition flex items-center gap-2 ${
                    s.id === this.active && !q
                        ? "bg-indigo-500/15 text-indigo-300 border border-indigo-500/30"
                        : "text-slate-400 hover:text-slate-200 hover:bg-white/5"
                }"><i data-lucide="${s.lucide}" class="w-4 h-4"></i> ${s.title}</button>`
        ).join("");

        let contentHtml = "";
        if (q) {
            const hits = [];
            sections.forEach((s) =>
                s.entries.forEach((e) => {
                    if (this._match(e, q)) hits.push({ s, e });
                })
            );
            contentHtml =
                `<p class="text-xs text-slate-500 mb-4">${hits.length} ⋅ „${this.query}"</p>` +
                (hits.length
                    ? hits.map(({ s, e }) => `
                <div class="glass-card p-5 mb-4">
                    <div class="text-[10px] uppercase tracking-wider text-slate-500 mb-1">${s.title}</div>
                    <h3 class="text-lg font-semibold text-white mb-2">${e.title}</h3>
                    <div class="text-sm text-slate-300 leading-relaxed">${e.body}</div>
                </div>`).join("")
                    : `<div class="text-slate-500 text-sm py-8 text-center">—</div>`);
        } else {
            const sec = sections.find((s) => s.id === this.active) || sections[0];
            contentHtml =
                `<h2 class="text-2xl font-bold text-gradient mb-4 flex items-center gap-2"><i data-lucide="${sec.lucide}" class="w-6 h-6"></i> ${sec.title}</h2>` +
                sec.entries.map((e) => `
                <div class="glass-card p-5 mb-4">
                    <h3 class="text-lg font-semibold text-white mb-2">${e.title}</h3>
                    <div class="text-sm text-slate-300 leading-relaxed">${e.body}</div>
                </div>`).join("");
        }

        this.screen.innerHTML = `
            <div class="w-full max-w-6xl mx-auto">
                <h1 class="text-3xl font-bold text-gradient mb-4 flex items-center gap-2"><i data-lucide="book-open" class="w-7 h-7"></i> ${this._tt("docs.title", "Centrum Dokumentacji")}</h1>
                <input id="docs-search" type="text" placeholder="${this._tt("docs.search", "🔎 Szukaj…")}" value="${this.query.replace(/"/g, "&quot;")}"
                    class="w-full bg-slate-900 border border-slate-700 rounded-lg p-3 text-white mb-6">
                <div class="flex gap-6">
                    <aside class="w-56 shrink-0 space-y-1">${sidebar}</aside>
                    <section class="flex-1 min-w-0">${contentHtml}</section>
                </div>
            </div>`;

        this._wire();
        if (window.lucide && window.lucide.createIcons) window.lucide.createIcons();
    }

    _wire() {
        const search = this.screen.querySelector("#docs-search");
        if (search) {
            search.oninput = (e) => {
                this.query = e.target.value;
                const pos = e.target.selectionStart;
                this.render();
                const s2 = this.screen.querySelector("#docs-search");
                if (s2) {
                    s2.focus();
                    try {
                        s2.setSelectionRange(pos, pos);
                    } catch (_) {}
                }
            };
        }
        this.screen.querySelectorAll("[data-doc-section]").forEach((btn) => {
            btn.onclick = () => {
                this.active = btn.getAttribute("data-doc-section");
                this.query = "";
                this.render();
            };
        });
    }
}

document.addEventListener("DOMContentLoaded", () => {
    window.AppDocs = new DocsCenter();
});
