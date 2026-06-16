// js/components/docs.js
// DOC-01: Centrum Dokumentacji — sekcje best-practice + wyszukiwarka + kompendium wiedzy.
// Treść wbudowana (offline-first), zgodna z realnym kodem. Głębsze materiały: linki do repo docs/.

const REPO = "https://github.com/PiotrSzym/SmartMyOdoo/blob/main";

const DOCS_SECTIONS = [
    {
        id: "start",
        icon: "🚀",
        title: "Start",
        entries: [
            {
                title: "Czym jest SmartMyOdoo",
                body: `<p>Middleware AI dla ERP <b>Odoo</b>: warstwa agentów (swarm) z bezpiecznym dostępem do danych.
                Łączy <b>bramę FastAPI</b>, rój agentów (Dispatcher → Executor → Pipeline), serwer <b>MCP</b>,
                szyfrowany <b>Skarbiec</b> (Vault), pseudonimizację <b>PII</b> (Presidio) i pamięć wektorową <b>RAG</b> (LanceDB).</p>`,
            },
            {
                title: "Uruchomienie serwera",
                body: `<p>Serwer (backend + UI z jednego procesu) startuj poleceniem:</p>
                <pre>python -m uvicorn smartmyodoo.api:app --host 127.0.0.1 --port 8000</pre>
                <p>⚠️ <b>Nie</b> używaj <code>python -m smartmyodoo.api</code> (uruchamia inną ścieżką).
                Panel: <code>http://127.0.0.1:8000</code>. Front jest serwowany przez backend (StaticFiles).</p>`,
            },
            {
                title: "Logowanie: PIN vs Master Password",
                body: `<ul class="list-disc pl-5 space-y-1">
                <li><b>PIN</b> (4 cyfry) — rola <i>user</i>: codzienna praca, odczyt sekretów.</li>
                <li><b>Master Password</b> — rola <i>admin</i>: reset PIN, operacje administracyjne.</li>
                <li>Zgubiony PIN zresetujesz Master Password. Utrata OBU = <b>bezpowrotna</b> utrata dostępu (AES nie ma furtki).</li>
                </ul>`,
            },
        ],
    },
    {
        id: "arch",
        icon: "🏛️",
        title: "Architektura",
        entries: [
            {
                title: "Brama FastAPI + routery domenowe",
                body: `<p><code>smartmyodoo/api.py</code> to cienki bootstrap (~95 l.): tworzy <code>app</code>, CORS,
                montuje routery i UI. Domeny są w <code>api_routers/</code>:
                <b>auth · secrets · chat · proposals · monitoring · workspaces · models</b>.</p>
                <p>Współdzielone zależności: <code>api_deps.py</code> (auth) i <code>chat_deps.py</code> (dispatcher/PII)
                — zerwany cykl importów (deps-module).</p>`,
            },
            {
                title: "Rój agentów (swarm)",
                body: `<ul class="list-disc pl-5 space-y-1">
                <li><b>Dispatcher</b> — klasyfikuje intencję, dobiera personę i model.</li>
                <li><b>SkillExecutor</b> — pętla tool-calling, sandbox, PII, audyt (jedna ścieżka polityk dla sync i stream).</li>
                <li><b>ExecutionPipeline</b> — FSM: Auth → Recon → Cognitive → Actuation → Teardown/Sync.</li>
                <li><b>MCP</b> — most narzędzi do Odoo (XML-RPC).</li>
                </ul>`,
            },
            {
                title: "Pamięć / RAG",
                body: `<p>Shared Brain: <b>LanceDB</b> (wektory) + SQLite (metadane). Chunking z <b>overlapem</b> po granicach zdań.
                Gdy baza/model niedostępne → tryb <b>zdegradowany</b> (jawny sygnał, brak fabrykowania kontekstu).</p>`,
            },
        ],
    },
    {
        id: "sec",
        icon: "🔐",
        title: "Bezpieczeństwo",
        entries: [
            {
                title: "Skarbiec — szyfrowanie (KEK/Fernet)",
                body: `<p>Kryptografia wielowarstwowa z <b>Key Encrypting Key</b>: losowy Vault Key (AES-128-CBC/Fernet)
                jest szyfrowany osobno PIN-em (<code>.pin_key</code>) i Master Password (<code>.master_key</code>, PBKDF2 480k).
                Plik <code>.vault_data</code> bez poprawnego hasła jest nieczytelny.</p>`,
            },
            {
                title: "PII — pseudonimizacja (RODO)",
                body: `<p>Dane osobowe są pseudonimizowane <b>zanim</b> trafią do LLM: <code>Jan Kowalski → &lt;PERSON_1&gt;</code>,
                <code>NIP 1234567890 → &lt;NIP_1&gt;</code> (odwracalnie, per workspace). Jedna kanoniczna warstwa: <code>security/pii/</code>.</p>`,
            },
            {
                title: "Sandbox fail-closed",
                body: `<p>Operacje zapisu na Odoo idą na <b>klon</b> bazy (scratchpad). Brak izolacji (np. brak master password)
                = <b>blokada zapisu</b>, nie zapis na produkcji. Koniec domyślnego hasła <code>admin</code>.</p>`,
            },
            {
                title: "TokenGovernor i distributed lock",
                body: `<ul class="list-disc pl-5 space-y-1">
                <li><b>TokenGovernor</b> — realna kontrola budżetu LLM (pre-flight hard-block + zapis kosztu).</li>
                <li><b>Distributed lock</b> (Redis <code>SET NX PX</code> + fallback proces-lokalny) — równoległe approve propozycji
                wykonają się <b>dokładnie raz</b> (anty-TOCTOU).</li>
                </ul>`,
            },
        ],
    },
    {
        id: "vault",
        icon: "🗝️",
        title: "Skarbiec & Klucze",
        entries: [
            {
                title: "Trzy typy kluczy (typowany rejestr)",
                body: `<ul class="list-disc pl-5 space-y-1">
                <li>🔑 <b>llm_provider</b> — klucz API modelu (provider: openrouter/anthropic/openai).</li>
                <li>🗄️ <b>odoo_data</b> — połączenie z Odoo do danych (url/baza/login/hasło).</li>
                <li>⏱️ <b>odoo_timesheet</b> — Odoo do czasu pracy (+ domyślny projekt/zadanie).</li>
                </ul>
                <p>Typ wybierasz w formularzu „Dodaj Sekret" (Skarbiec); ikona typu pokazuje się na liście.</p>`,
            },
            {
                title: "Jak AI bierze credentials bez znajomości haseł",
                body: `<p>Agent <b>nigdy</b> nie widzi haseł. System wstrzykuje sekrety ze Skarbca do środowiska wykonania
                w locie (po autoryzacji PIN/Master), a do LLM idą tylko pseudonimizowane treści. Resolver dobiera właściwy
                klucz wg typu i workspace (timesheet → data → legacy).</p>`,
            },
        ],
    },
    {
        id: "models",
        icon: "⚙️",
        title: "Modele AI",
        entries: [
            {
                title: "Tiery kosztów (routing per skill)",
                body: `<ul class="list-disc pl-5 space-y-1">
                <li><b>CHEAP</b> — klasyfikacja, krótkie odpowiedzi.</li>
                <li><b>STANDARD</b> — typowy dev/CRUD.</li>
                <li><b>PREMIUM</b> — architektura, trudny audyt.</li>
                </ul>
                <p>Edycja w zakładce <b>⚙️ Modele</b> (tier→model, budżet, mapa skill→tier). Backend: <code>GET/PUT /api/models/policy</code>.</p>`,
            },
            {
                title: "Odporność i wydajność",
                body: `<ul class="list-disc pl-5 space-y-1">
                <li><b>Retry + fallback</b> model (przejściowy błąd nie wywala zapytania) + exp backoff.</li>
                <li><b>Cache</b> odpowiedzi (In-Memory/Redis) — identyczne zapytanie nie generuje kosztu.</li>
                <li><b>Degradacja budżetu</b> — przy niskim budżecie tier schodzi (PREMIUM→STANDARD→CHEAP) zamiast blokady.</li>
                </ul>`,
            },
        ],
    },
    {
        id: "skills",
        icon: "🧠",
        title: "Skille & Agenci",
        entries: [
            {
                title: "Persony i Skill Panel",
                body: `<p>Specjalizacje (Business Analyst, Developer, DevOps, Audyt, CRUD, ETL, Finance, Security…) z barierami
                <code>read_only</code> / <code>requires_shadow_mode</code> / <code>requires_human_override</code>.
                W zakładce <b>Skille</b> możesz wybrać role ręcznie (bypass auto-dispatchera).</p>`,
            },
            {
                title: "Shadow Mode (akceptacja operacji)",
                body: `<p>Operacje na bazie wymagają akceptacji: agent proponuje (Proposal), Ty zatwierdzasz w UI.
                Approve jest <b>idempotentne</b> i chronione lockiem — żadnego podwójnego wykonania.</p>`,
            },
        ],
    },
    {
        id: "sprints",
        icon: "🛠️",
        title: "Sprinty & Roadmap",
        entries: [
            {
                title: "Zrealizowane sprinty",
                body: `<ul class="list-disc pl-5 space-y-1">
                <li><b>FIX-01</b> — remediacja audytu (PII, sandbox, CORS, reality-check atrap).</li>
                <li><b>KEY-01</b> — typowany rejestr kluczy + routing modeli + UI (K1-K6).</li>
                <li><b>FIX-02</b> — Struktura (api.py 712→95 l., dedup executora, PII, deps-module) + Patterny (cache, lock, RAG). Suita <b>240 testów</b>.</li>
                </ul>`,
            },
            {
                title: "Dokumenty w repozytorium",
                body: `<ul class="list-disc pl-5 space-y-1">
                <li><a class="text-indigo-400 underline" target="_blank" href="${REPO}/docs/README.md">📚 Indeks dokumentacji</a></li>
                <li><a class="text-indigo-400 underline" target="_blank" href="${REPO}/CHANGELOG.md">CHANGELOG</a></li>
                <li><a class="text-indigo-400 underline" target="_blank" href="${REPO}/docs/sprints">Wszystkie sprinty</a></li>
                <li><a class="text-indigo-400 underline" target="_blank" href="${REPO}/docs/guides/odoo_docker_environment.md">Przewodnik Odoo Docker</a></li>
                </ul>`,
            },
        ],
    },
    {
        id: "kb",
        icon: "📚",
        title: "Kompendium wiedzy",
        entries: [
            {
                title: "Odoo: edycje i hosting",
                body: `<ul class="list-disc pl-5 space-y-1">
                <li><b>Community</b> (open-source) vs <b>Enterprise</b> (płatne moduły, studio, księgowość pełna).</li>
                <li>Hosting: <b>Odoo SaaS</b> (online, ograniczenia kodu), <b>Odoo.sh</b> (PaaS, git+staging), <b>On-Premise</b> (pełna kontrola).</li>
                <li>Wersje 16/17/18/19 — uważaj na zgodność modułów i API XML-RPC.</li>
                </ul>`,
            },
            {
                title: "Pułapki Odoo (best practice)",
                body: `<ul class="list-disc pl-5 space-y-1">
                <li><b>Nie modyfikuj rdzenia</b> — dziedzicz (<code>_inherit</code>), nigdy edycji core.</li>
                <li><b>Magic Tuples</b> w polach relacyjnych: <code>(0,0,{})</code> tworzy, <code>(4,id)</code> łączy, <code>(6,0,[ids])</code> zastępuje.</li>
                <li><b>Lock Dates</b> w księgowości — operacje wstecz blokowane; używaj not kredytowych.</li>
                <li><b>Batching</b> przy imporcie (np. 200 rek/żądanie) — omijasz timeouty i limity pamięci.</li>
                <li>Logi Odoo.sh czytaj <b>bottom-up</b> (od dołu) — szybciej znajdziesz korzeń błędu.</li>
                </ul>`,
            },
            {
                title: "FAQ",
                body: `<ul class="list-disc pl-5 space-y-1">
                <li><b>Czy AI widzi moje hasła?</b> Nie — sekrety wstrzykiwane są w locie, do LLM idą tylko pseudonimy.</li>
                <li><b>Na jakim porcie działa panel?</b> <code>http://127.0.0.1:8000</code>.</li>
                <li><b>Skąd AI wie, którego modelu użyć?</b> Z polityki tierów per skill (zakładka ⚙️ Modele).</li>
                <li><b>Co gdy brak klucza OpenRouter?</b> Dispatcher przechodzi w tryb heurystyczny (offline), bez wywołań LLM.</li>
                </ul>`,
            },
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
        const hay = (entry.title + " " + entry.body).toLowerCase();
        return hay.includes(q);
    }

    render() {
        const q = this.query.trim().toLowerCase();
        const sidebar = DOCS_SECTIONS.map(
            (s) => `
            <button data-doc-section="${s.id}"
                class="w-full text-left px-3 py-2 rounded-lg text-sm transition ${
                    s.id === this.active && !q
                        ? "bg-indigo-500/15 text-indigo-300 border border-indigo-500/30"
                        : "text-slate-400 hover:text-slate-200 hover:bg-white/5"
                }">${s.icon} ${s.title}</button>`
        ).join("");

        let contentHtml = "";
        if (q) {
            // tryb wyszukiwania — wpisy ze wszystkich sekcji
            const hits = [];
            DOCS_SECTIONS.forEach((s) =>
                s.entries.forEach((e) => {
                    if (this._match(e, q)) hits.push({ s, e });
                })
            );
            contentHtml =
                `<p class="text-xs text-slate-500 mb-4">Wyniki wyszukiwania: <b>${hits.length}</b></p>` +
                (hits.length
                    ? hits
                          .map(
                              ({ s, e }) => `
                <div class="glass-card p-5 mb-4">
                    <div class="text-[10px] uppercase tracking-wider text-slate-500 mb-1">${s.icon} ${s.title}</div>
                    <h3 class="text-lg font-semibold text-white mb-2">${e.title}</h3>
                    <div class="text-sm text-slate-300 leading-relaxed">${e.body}</div>
                </div>`
                          )
                          .join("")
                    : `<div class="text-slate-500 text-sm py-8 text-center">Brak wyników dla „${this.query}".</div>`);
        } else {
            const sec = DOCS_SECTIONS.find((s) => s.id === this.active) || DOCS_SECTIONS[0];
            contentHtml =
                `<h2 class="text-2xl font-bold text-gradient mb-4">${sec.icon} ${sec.title}</h2>` +
                sec.entries
                    .map(
                        (e) => `
                <div class="glass-card p-5 mb-4">
                    <h3 class="text-lg font-semibold text-white mb-2">${e.title}</h3>
                    <div class="text-sm text-slate-300 leading-relaxed">${e.body}</div>
                </div>`
                    )
                    .join("");
        }

        this.screen.innerHTML = `
            <div class="w-full max-w-6xl mx-auto">
                <div class="flex justify-between items-center mb-4">
                    <h1 class="text-3xl font-bold text-gradient">📖 Centrum Dokumentacji</h1>
                </div>
                <input id="docs-search" type="text" placeholder="🔎 Szukaj w dokumentacji…" value="${this.query.replace(/"/g, "&quot;")}"
                    class="w-full bg-slate-900 border border-slate-700 rounded-lg p-3 text-white mb-6">
                <div class="flex gap-6">
                    <aside class="w-56 shrink-0 space-y-1">${sidebar}</aside>
                    <section class="flex-1 min-w-0">${contentHtml}</section>
                </div>
            </div>`;

        this._wire();
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
