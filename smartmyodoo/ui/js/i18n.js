/**
 * I18N-01: lekka wielojęzyczność bez build-stepu.
 * - Słownik I18N = { pl: {...}, en: {...} } (klucze dotted).
 * - t(key) — tłumaczenie wg AppStore.lang (fallback: pl → klucz).
 * - applyI18n(root) — podstawia teksty w [data-i18n] / [data-i18n-title] / [data-i18n-ph].
 * - Przełącznik języka renderowany do #lang-switch; zapis w localStorage.
 * Dodanie języka = nowy zestaw kluczy w I18N + wpis w LANGS.
 */

const LANGS = [
    { code: "pl", label: "PL" },
    { code: "en", label: "EN" },
];

const I18N = {
    pl: {
        "nav.vault": "Skarbiec",
        "nav.chat": "Czat",
        "nav.activity": "Aktywność",
        "nav.project": "Projekt",
        "nav.skills": "Skille",
        "nav.models": "Modele",
        "nav.docs": "Dokumentacja",
        "tip.vault": "Skarbiec — szyfrowane sekrety i klucze (Vault)",
        "tip.chat": "Czat z agentami AI (z odpowiedziami na żywo)",
        "tip.activity": "Aktywność — oś czasu wywołań narzędzi i audyt",
        "tip.project": "Projekt — połączenie z Odoo/Jira, Task Picker, czas pracy",
        "tip.skills": "Skille — ręczny wybór wyspecjalizowanych agentów",
        "tip.models": "Modele AI — tiery kosztów, budżet, routing per skill",
        "tip.docs": "Dokumentacja — sekcje, wyszukiwarka, kompendium",
        "tip.theme": "Zmień motyw",
        "login.subtitle": "Wprowadź PIN lub Master Password aby odblokować.",
        "login.placeholder": "••••••••",
        "login.unlock": "Odblokuj",
        "login.error": "Nieprawidłowe hasło",
        "vault.docs": "Dokumentacja",
        "vault.changePin": "Resetuj PIN (Admin)",
        "vault.logout": "Zablokuj Sejf",
        "vault.search": "Szukaj sekretu...",
        "common.save": "Zapisz",
        "common.cancel": "Anuluj",
        "common.add": "Dodaj",
        "secret.add": "Dodaj Sekret",
        "secret.save": "Zapisz do Skarbca",
        "secret.type": "Typ Klucza",
        "secret.name": "Nazwa Klucza (Używana w ENV)",
        "models.title": "Modele AI",
        "models.save": "Zapisz politykę",
        "docs.search": "🔎 Szukaj w dokumentacji…",
        "docs.title": "Centrum Dokumentacji",
        "chat.welcome": "Witaj w panelu SmartMyOdoo HUB! 🔒 Połączenie zabezpieczone. Aktywna przestrzeń: {ws}. W czym mogę pomóc?",
        "chat.welcomeTitle": "Witaj w SmartMyOdoo",
        "chat.placeholder": "Napisz polecenie dla Agenta...",
        "chat.noHistory": "Brak historii sesji.",
        "chat.newSession": "Nowa sesja",
        "chat.noReply": "Brak odpowiedzi.",
        "chat.newSessionStarted": "Rozpoczęto nową sesję konwersacji. W czym mogę pomóc?",
        "activity.title": "Aktywność Agenta",
        "activity.empty": "Brak aktywności w tym workspace.",
    },
    en: {
        "nav.vault": "Vault",
        "nav.chat": "Chat",
        "nav.activity": "Activity",
        "nav.project": "Project",
        "nav.skills": "Skills",
        "nav.models": "Models",
        "nav.docs": "Docs",
        "tip.vault": "Vault — encrypted secrets and keys",
        "tip.chat": "Chat with AI agents (live streaming replies)",
        "tip.activity": "Activity — tool-call timeline and audit",
        "tip.project": "Project — Odoo/Jira connection, Task Picker, timesheets",
        "tip.skills": "Skills — manually pick specialized agents",
        "tip.models": "AI Models — cost tiers, budget, per-skill routing",
        "tip.docs": "Docs — sections, search, knowledge base",
        "tip.theme": "Toggle theme",
        "login.subtitle": "Enter your PIN or Master Password to unlock.",
        "login.placeholder": "••••••••",
        "login.unlock": "Unlock",
        "login.error": "Invalid password",
        "vault.docs": "Docs",
        "vault.changePin": "Reset PIN (Admin)",
        "vault.logout": "Lock Vault",
        "vault.search": "Search secret...",
        "common.save": "Save",
        "common.cancel": "Cancel",
        "common.add": "Add",
        "secret.add": "Add Secret",
        "secret.save": "Save to Vault",
        "secret.type": "Key Type",
        "secret.name": "Key Name (used in ENV)",
        "models.title": "AI Models",
        "models.save": "Save policy",
        "docs.search": "🔎 Search the docs…",
        "docs.title": "Documentation Center",
        "chat.welcome": "Welcome to the SmartMyOdoo HUB! 🔒 Secure connection. Active workspace: {ws}. How can I help?",
        "chat.welcomeTitle": "Welcome to SmartMyOdoo",
        "chat.placeholder": "Type a command for the Agent...",
        "chat.noHistory": "No session history.",
        "chat.newSession": "New session",
        "chat.noReply": "No response.",
        "chat.newSessionStarted": "Started a new conversation. How can I help?",
        "activity.title": "Agent Activity",
        "activity.empty": "No activity in this workspace.",
    },
};

function _lang() {
    try {
        return (window.AppStore && AppStore.getState().lang) || "pl";
    } catch (_) {
        return "pl";
    }
}

function t(key) {
    const lang = _lang();
    return (I18N[lang] && I18N[lang][key]) || I18N.pl[key] || key;
}

function applyI18n(root) {
    const scope = root || document;
    scope.querySelectorAll("[data-i18n]").forEach((el) => {
        el.textContent = t(el.getAttribute("data-i18n"));
    });
    scope.querySelectorAll("[data-i18n-title]").forEach((el) => {
        el.setAttribute("title", t(el.getAttribute("data-i18n-title")));
    });
    scope.querySelectorAll("[data-i18n-ph]").forEach((el) => {
        el.setAttribute("placeholder", t(el.getAttribute("data-i18n-ph")));
    });
    // odśwież ikony Lucide (textContent mógł nie ruszyć SVG, ale dla pewności)
    if (window.lucide && window.lucide.createIcons) window.lucide.createIcons();
}

function setLang(code) {
    if (!I18N[code]) return;
    try {
        localStorage.setItem("smartmyodoo_lang", code);
    } catch (_) {}
    AppStore.setState({ lang: code });
}

function renderLangSwitch() {
    const host = document.getElementById("lang-switch");
    if (!host) return;
    const cur = _lang();
    host.innerHTML = LANGS.map(
        (l) =>
            `<button data-lang="${l.code}" class="px-2 py-1 text-xs rounded ${
                l.code === cur
                    ? "bg-indigo-500/20 text-indigo-300 border border-indigo-500/30"
                    : "text-slate-400 hover:text-slate-200"
            }">${l.label}</button>`
    ).join("");
    host.querySelectorAll("[data-lang]").forEach((b) => {
        b.onclick = () => setLang(b.getAttribute("data-lang"));
    });
}

// Eksport globalny
window.t = t;
window.applyI18n = applyI18n;
window.setLang = setLang;

document.addEventListener("DOMContentLoaded", () => {
    // wczytaj zapamiętany język PRZED pierwszym renderem zależnych komponentów
    let saved = "pl";
    try {
        saved = localStorage.getItem("smartmyodoo_lang") || "pl";
    } catch (_) {}
    if (window.AppStore) AppStore.setState({ lang: saved });

    applyI18n(document);
    renderLangSwitch();

    // reakcja na zmianę języka: przetłumacz statyczny HTML + odśwież przełącznik
    if (window.AppStore) {
        AppStore.subscribe((ns, os) => {
            if (ns.lang !== os.lang) {
                applyI18n(document);
                renderLangSwitch();
                // komponenty dynamiczne re-renderują się same (subskrypcja lang)
                if (window.AppDocs) window.AppDocs.render();
            }
        });
    }
});
