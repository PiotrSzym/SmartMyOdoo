// js/components/docs.js
// DOC-01 / DOC-02: Centrum Dokumentacji — sekcje + wyszukiwarka + kompendium.
// Treść oparta na REALNYCH sprintach i funkcjach (HUB, swarm, MCP, Vault, RAG, pipeline).
// Ikony sekcji: Lucide (data-lucide) — renderowane przez lucide.createIcons() po każdym render().

const REPO = "https://github.com/PiotrSzym/SmartMyOdoo/blob/main";

// 11 wyspecjalizowanych agentów (rejestr SkillName + opisy z /api/skills)
const AGENTS = [
    ["📊", "Business Analyst", "Standard First", "Analiza biznesowa, architektura procesów i konfiguracja Standard Odoo <b>bez pisania kodu</b>. Wzywaj pierwszego przy projektowaniu modułu."],
    ["💻", "Developer", "_inherit, no core mod", "Bezpieczne zmiany kodu przez dziedziczenie (<code>_inherit</code>), ORM, zero modyfikacji rdzenia."],
    ["🚀", "DevOps / GitHub", "Staging isolation", "Repozytorium, feature branches, CI/CD, izolowane środowiska staging przed produkcją."],
    ["📋", "SH Logs", "Tracebacki bottom-up", "Odoo.sh i błędy krytyczne — czyta tracebacki od dołu, by szybko znaleźć korzeń błędu."],
    ["🔍", "Audit History", "chatter / mail.message", "Śledzi kto/co/kiedy zmienił przez wewnętrzny komunikator (chatter, <code>mail.message</code>)."],
    ["🗄️", "CRUD", "Magic Tuples", "Manipulacja danymi i relacjami: <code>(0,0,{})</code> tworzy, <code>(4,id)</code> łączy, <code>(6,0,[…])</code> zastępuje."],
    ["📦", "ETL Manager", "Batching 200/req", "Wielkie migracje/importy ze stronicowaniem (np. 200 rek/żądanie) — omija limity i timeouty."],
    ["💰", "Financial Audit", "Lock Dates", "Księgowość: noty kredytowe, daty blokady, bezpieczeństwo operacji finansowych."],
    ["🔒", "Security Audit", "PII / RODO", "Luki (Record Rules), RODO, szyfrowanie, anonimizacja i pseudonimizacja danych PII."],
    ["🔌", "API Expert", "XML-RPC / REST", "Integracje zewnętrzne, bezpieczne API Keys, koniec niebezpiecznego <code>auth=public</code>."],
    ["🪄", "Magic Fix", "Force unlock, kryzys", "Zadania ratunkowe: siłowe odblokowanie locków, uwalnianie cronów, przywracanie środowisk."],
];

const DOCS_SECTIONS = [
    {
        id: "start", lucide: "rocket", icon: "🚀", title: "Start",
        entries: [
            { title: "Czym jest SmartMyOdoo", body: `<p>Middleware AI dla ERP <b>Odoo</b>: rój wyspecjalizowanych agentów z bezpiecznym dostępem do danych.
                Łączy <b>bramę FastAPI</b>, swarm (Dispatcher → Executor → Pipeline), serwer <b>MCP</b> (most do Odoo),
                szyfrowany <b>Skarbiec</b>, pseudonimizację <b>PII</b> i pamięć wektorową <b>RAG</b>. Praca w wielu
                <b>przestrzeniach roboczych</b> (multi-workspace) powiązanych z zadaniami Odoo/Jira.</p>` },
            { title: "Uruchomienie serwera", body: `<pre>python -m uvicorn smartmyodoo.api:app --host 127.0.0.1 --port 8000</pre>
                <p>Panel: <code>http://127.0.0.1:8000</code>. Front serwowany przez backend (jeden proces).
                ⚠️ Nie używaj <code>python -m smartmyodoo.api</code>.</p>` },
            { title: "Logowanie: PIN vs Master", body: `<ul class="list-disc pl-5 space-y-1">
                <li><b>PIN</b> (4 cyfry) — rola <i>user</i>: codzienna praca.</li>
                <li><b>Master Password</b> — rola <i>admin</i>: reset PIN, administracja.</li>
                <li>Utrata OBU = bezpowrotna utrata dostępu (AES bez furtki).</li></ul>` },
            { title: "CLI (tryb klient-serwer)", body: `<p>Interaktywne CLI (Rich + prompt_toolkit) łączy się z backendem przez HTTP/WebSocket
                (F7-02). Ta sama logika co panel, w terminalu.</p>` },
        ],
    },
    {
        id: "features", lucide: "layout-grid", icon: "🧩", title: "Funkcje",
        entries: [
            { title: "Multi-Workspace HUB", body: `<p>Wiele projektów jednocześnie (styl Discord/Slack). Każdy workspace ma własną konfigurację,
                poświadczenia i <b>Lessons Learned</b> — wracasz podając tylko PIN, agenci mają od razu kontekst.</p>` },
            { title: "Project Hub + Task Picker", body: `<p>Kreator połączeń (Odoo v16 / Jira) z testem połączenia i zapisem do Skarbca.
                Wyszukiwarka zadań z autouzupełnianiem (XML-RPC <code>project.task</code>): nazwa, klient, osoba, status.</p>` },
            { title: "Auto-Timesheets + Raport miesięczny", body: `<p>Czas pracy (estymowany/rzeczywisty/hybrydowy) — przy zamknięciu workspace system tworzy wpis
                Timesheet w Odoo (<code>hr.analytic.line</code>) z notatką AI. Raport miesięczny: godziny + koszty tokenów per klient, eksport CSV.</p>` },
            { title: "AI Session Summary + sync dwukierunkowa", body: `<p>Po sesji AI generuje raport z Audit Logu i wysyła jako komentarz (<code>mail.message</code>) do zadania.
                Zamknięcie workspace → opcjonalna zmiana statusu zadania w Odoo (polling 60s).</p>` },
            { title: "Shadow Mode (akceptacja operacji)", body: `<p>Operacje na bazie wymagają akceptacji: agent proponuje (Proposal), Ty zatwierdzasz w UI.
                Approve jest <b>idempotentne</b> i chronione distributed lockiem — zero podwójnego wykonania.</p>` },
            { title: "Czat + streaming na żywo", body: `<p>Czat z agentami, odpowiedzi <b>strumieniowane</b> przez WebSocket (tokeny, logi narzędzi, stany FSM pipeline).
                Badge pokazuje, który model obsłużył odpowiedź.</p>` },
            { title: "Fireflies AI Connector", body: `<p>4-krokowy kaskadowy algorytm dopasowywania spotkań + webhook REST — wiedza ze spotkań trafia do kontekstu.</p>` },
            { title: "Audit Trail + Aktywność", body: `<p>Każde wywołanie narzędzia logowane (z filtrem sekretów) — live timeline w zakładce Aktywność, zapis do bazy.</p>` },
        ],
    },
    {
        id: "arch", lucide: "building-2", icon: "🏛️", title: "Architektura",
        entries: [
            { title: "Brama FastAPI + routery domenowe", body: `<p><code>api.py</code> to cienki bootstrap (~95 l.); domeny w <code>api_routers/</code>:
                <b>auth · secrets · chat · proposals · monitoring · workspaces · models</b>. Wspólne zależności: <code>api_deps</code>/<code>chat_deps</code> (deps-module, brak cyklu importów).</p>` },
            { title: "Rój agentów (swarm)", body: `<ul class="list-disc pl-5 space-y-1">
                <li><b>Dispatcher</b> — klasyfikuje intencję, dobiera personę i model.</li>
                <li><b>SkillExecutor</b> — pętla tool-calling, sandbox, PII, audyt (jedna ścieżka polityk dla sync i stream).</li>
                <li><b>ExecutionPipeline</b> (FSM) — Auth → Recon → Cognitive → Actuation → Teardown/Sync, z wstrzykiwaniem rozpoznania środowiska (ADP, 8 kroków).</li>
                <li><b>MCP</b> — most narzędzi do Odoo (XML-RPC).</li></ul>` },
            { title: "Pamięć / RAG (Shared Brain)", body: `<p>LanceDB (wektory) + SQLite (metadane). Chunking z <b>overlapem</b> po granicach zdań;
                przy braku bazy/modelu — tryb <b>zdegradowany</b> (jawny sygnał, brak fabrykowania kontekstu).</p>` },
            { title: "Kolejka i workery (Redis)", body: `<p>Niezawodna kolejka zadań (BLMOVE + ack + requeue stale, TTL) i workery z uczciwymi handlerami + graceful shutdown.</p>` },
        ],
    },
    {
        id: "agents", lucide: "users", icon: "🧠", title: "Agenci (11)",
        entries: [
            { title: "Wyspecjalizowane persony", body: `<p>System ma <b>11 wyspecjalizowanych agentów</b>. Dispatcher dobiera właściwego automatycznie,
                albo wybierasz ręcznie w zakładce <b>Skille</b> (bypass auto-routingu). Każdy ma bariery
                <code>read_only</code> / <code>shadow_mode</code> / <code>human_override</code>.</p>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-2 mt-3">
                ${AGENTS.map(([ic, name, tag, desc]) => `
                    <div class="bg-black/20 rounded-lg p-3">
                        <div class="font-semibold text-white">${ic} ${name} <span class="text-[10px] text-slate-500 font-mono">${tag}</span></div>
                        <div class="text-xs text-slate-400 mt-1">${desc}</div>
                    </div>`).join("")}
                </div>` },
            { title: "Routing modeli per agent", body: `<p>Każdy agent ma przypisany <b>poziom kosztu</b> (CHEAP/STANDARD/PREMIUM). Dispatcher zawsze tani;
                audyty finansowe/security i architektura → PREMIUM. Patrz zakładka ⚙️ Modele.</p>` },
        ],
    },
    {
        id: "sec", lucide: "shield", icon: "🔐", title: "Bezpieczeństwo",
        entries: [
            { title: "Skarbiec — szyfrowanie (KEK/Fernet)", body: `<p>Klucz główny (AES-128/Fernet) szyfrowany osobno PIN-em i Master Password (PBKDF2 480k).
                Plik <code>.vault_data</code> bez hasła jest nieczytelny.</p>` },
            { title: "PII — pseudonimizacja (RODO)", body: `<p>Dane osobowe pseudonimizowane <b>zanim</b> trafią do LLM: <code>Jan Kowalski → &lt;PERSON_1&gt;</code> (odwracalnie, per workspace).
                Jedna kanoniczna warstwa <code>security/pii/</code>.</p>` },
            { title: "Sandbox fail-closed", body: `<p>Zapisy do Odoo idą na <b>klon</b> bazy (scratchpad). Brak izolacji = <b>blokada zapisu</b>, nie zapis na produkcji.</p>` },
            { title: "TokenGovernor + distributed lock", body: `<ul class="list-disc pl-5 space-y-1">
                <li><b>TokenGovernor</b> — realna kontrola budżetu LLM (pre-flight + zapis kosztu).</li>
                <li><b>Distributed lock</b> (Redis <code>SET NX PX</code> + fallback) — anty-TOCTOU na approve.</li>
                <li>CORS jawne originy + rate-limit/lockout logowania.</li></ul>` },
        ],
    },
    {
        id: "vault", lucide: "key-round", icon: "🗝️", title: "Skarbiec & Klucze",
        entries: [
            { title: "Trzy typy kluczy", body: `<ul class="list-disc pl-5 space-y-1">
                <li>🔑 <b>llm_provider</b> — klucz API modelu (openrouter/anthropic/openai).</li>
                <li>🗄️ <b>odoo_data</b> — połączenie z Odoo do danych.</li>
                <li>⏱️ <b>odoo_timesheet</b> — Odoo do czasu pracy (+ domyślny projekt/zadanie).</li></ul>
                <p>Typ wybierasz w „Dodaj Sekret"; ikona typu pokazuje się na liście.</p>` },
            { title: "Jak AI bierze credentials bez haseł", body: `<p>Agent nigdy nie widzi haseł — sekrety wstrzykiwane są do środowiska wykonania w locie (po autoryzacji),
                a do LLM idą tylko pseudonimy. Resolver dobiera klucz wg typu i workspace (timesheet → data → legacy).</p>` },
        ],
    },
    {
        id: "models", lucide: "sliders-horizontal", icon: "⚙️", title: "Modele AI",
        entries: [
            { title: "Tiery kosztów (routing per skill)", body: `<ul class="list-disc pl-5 space-y-1">
                <li><b>CHEAP</b> — klasyfikacja, krótkie odpowiedzi.</li><li><b>STANDARD</b> — typowy dev/CRUD.</li>
                <li><b>PREMIUM</b> — architektura, trudny audyt.</li></ul>
                <p>Edycja w zakładce <b>⚙️ Modele</b> (tier→model, budżet, mapa skill→tier). Backend: <code>GET/PUT /api/models/policy</code>.</p>` },
            { title: "Odporność i wydajność", body: `<ul class="list-disc pl-5 space-y-1">
                <li><b>Retry + fallback</b> model + exp backoff.</li>
                <li><b>Cache</b> odpowiedzi (In-Memory/Redis) — identyczne zapytanie bez kosztu.</li>
                <li><b>Degradacja budżetu</b> — przy niskim budżecie tier schodzi zamiast blokady.</li></ul>` },
        ],
    },
    {
        id: "kb", lucide: "book-open", icon: "📚", title: "Kompendium wiedzy",
        entries: [
            { title: "Odoo: edycje i hosting", body: `<ul class="list-disc pl-5 space-y-1">
                <li><b>Community</b> (open-source) vs <b>Enterprise</b> (studio, pełna księgowość).</li>
                <li>Hosting: <b>SaaS</b> (online), <b>Odoo.sh</b> (PaaS, git+staging), <b>On-Premise</b> (pełna kontrola).</li>
                <li>Wersje 16/17/18/19 — uważaj na zgodność modułów i API.</li></ul>` },
            { title: "Pułapki Odoo (best practice)", body: `<ul class="list-disc pl-5 space-y-1">
                <li><b>Nie modyfikuj rdzenia</b> — dziedzicz (<code>_inherit</code>).</li>
                <li><b>Magic Tuples</b>: <code>(0,0,{})</code>, <code>(4,id)</code>, <code>(6,0,[ids])</code>.</li>
                <li><b>Lock Dates</b> — operacje wstecz blokowane; używaj not kredytowych.</li>
                <li><b>Batching</b> importu (200 rek/żądanie) — omijasz timeouty.</li>
                <li>Logi Odoo.sh czytaj <b>bottom-up</b>.</li></ul>` },
            { title: "FAQ", body: `<ul class="list-disc pl-5 space-y-1">
                <li><b>Czy AI widzi hasła?</b> Nie — wstrzykiwane w locie, do LLM tylko pseudonimy.</li>
                <li><b>Port panelu?</b> <code>http://127.0.0.1:8000</code>.</li>
                <li><b>Brak klucza OpenRouter?</b> Dispatcher przechodzi w tryb heurystyczny (offline).</li>
                <li><b>Pełna dokumentacja?</b> <a class="text-indigo-400 underline" target="_blank" href="${REPO}/docs/README.md">repo docs/</a> · <a class="text-indigo-400 underline" target="_blank" href="${REPO}/CHANGELOG.md">CHANGELOG</a>.</li></ul>` },
        ],
    },
];

class DocsCenter {
    constructor() {
        this.screen = document.getElementById("docs-screen");
        this.active = "start";
        this.query = "";
        if (this.screen) this.render();
    }

    _match(entry, q) {
        return (entry.title + " " + entry.body).toLowerCase().includes(q);
    }

    _icons() {
        // Lucide: zamień <i data-lucide> na SVG po wstawieniu HTML
        if (window.lucide && typeof window.lucide.createIcons === "function") {
            window.lucide.createIcons();
        }
    }

    render() {
        const q = this.query.trim().toLowerCase();
        const sidebar = DOCS_SECTIONS.map(
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
            DOCS_SECTIONS.forEach((s) =>
                s.entries.forEach((e) => {
                    if (this._match(e, q)) hits.push({ s, e });
                })
            );
            contentHtml =
                `<p class="text-xs text-slate-500 mb-4">Wyniki: <b>${hits.length}</b></p>` +
                (hits.length
                    ? hits.map(({ s, e }) => `
                <div class="glass-card p-5 mb-4">
                    <div class="text-[10px] uppercase tracking-wider text-slate-500 mb-1">${s.icon} ${s.title}</div>
                    <h3 class="text-lg font-semibold text-white mb-2">${e.title}</h3>
                    <div class="text-sm text-slate-300 leading-relaxed">${e.body}</div>
                </div>`).join("")
                    : `<div class="text-slate-500 text-sm py-8 text-center">Brak wyników dla „${this.query}".</div>`);
        } else {
            const sec = DOCS_SECTIONS.find((s) => s.id === this.active) || DOCS_SECTIONS[0];
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
                <h1 class="text-3xl font-bold text-gradient mb-4 flex items-center gap-2"><i data-lucide="book-open" class="w-7 h-7"></i> Centrum Dokumentacji</h1>
                <input id="docs-search" type="text" placeholder="🔎 Szukaj w dokumentacji…" value="${this.query.replace(/"/g, "&quot;")}"
                    class="w-full bg-slate-900 border border-slate-700 rounded-lg p-3 text-white mb-6">
                <div class="flex gap-6">
                    <aside class="w-56 shrink-0 space-y-1">${sidebar}</aside>
                    <section class="flex-1 min-w-0">${contentHtml}</section>
                </div>
            </div>`;

        this._wire();
        this._icons();
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
