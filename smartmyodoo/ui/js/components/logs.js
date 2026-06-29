// js/components/logs.js
// SH-LOG-01: zakładka „Logi" — wkleja log Odoo.sh, woła POST /api/logs/parse
// i renderuje wynik: root cause (bottom-up) na górze, błędy HTTP 5xx, podsumowanie
// poziomów i pełną listę wpisów z tracebackami. Vanilla-JS (ADR-006), authFetch z api.js.

const LEVEL_STYLE = {
    CRITICAL: 'bg-red-500/20 text-red-300 border-red-500/40',
    ERROR: 'bg-red-500/15 text-red-300 border-red-500/30',
    WARNING: 'bg-amber-500/15 text-amber-300 border-amber-500/30',
    INFO: 'bg-slate-500/15 text-slate-300 border-slate-600/40',
    DEBUG: 'bg-slate-700/30 text-slate-400 border-slate-700/50',
};

function _esc(s) {
    // Reużyj globalnego escapeHtml (project.js); fallback gdyby nie był załadowany.
    if (typeof escapeHtml === 'function') return escapeHtml(s);
    return String(s == null ? '' : s)
        .replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;');
}

function clearLogs() {
    const input = document.getElementById('logs-input');
    const results = document.getElementById('logs-results');
    const hint = document.getElementById('logs-hint');
    if (input) input.value = '';
    if (results) results.innerHTML = '';
    if (hint) hint.textContent = '';
}

async function parseLogs() {
    const input = document.getElementById('logs-input');
    const results = document.getElementById('logs-results');
    const hint = document.getElementById('logs-hint');
    const btn = document.getElementById('logs-parse-btn');
    if (!input || !results) return;

    const text = input.value;
    if (!text.trim()) {
        if (typeof showToast === 'function') showToast('Wklej najpierw log Odoo.sh.');
        return;
    }

    btn.disabled = true;
    const prevLabel = btn.textContent;
    btn.textContent = 'Analizuję…';
    results.innerHTML = '';
    if (hint) hint.textContent = '';

    try {
        const res = await authFetch('/api/logs/parse', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text }),
        });
        if (!res.ok) {
            const detail = await res.json().catch(() => ({}));
            results.innerHTML = renderError(res.status, detail.detail || res.statusText);
            return;
        }
        const data = await res.json();
        renderLogReport(data, results, hint);
    } catch (e) {
        results.innerHTML = renderError('—', e.message);
    } finally {
        btn.disabled = false;
        btn.textContent = prevLabel;
    }
}

function renderError(status, msg) {
    return `<div class="glass-card p-5 border border-red-500/30 bg-red-900/10 text-red-300 text-sm">
        ❌ Błąd analizy (${_esc(status)}): ${_esc(msg)}</div>`;
}

function renderLogReport(data, results, hint) {
    const s = data.summary || {};
    const entries = data.entries || [];

    if ((s.parsed_entries || 0) === 0) {
        results.innerHTML = `<div class="glass-card p-5 text-slate-400 text-sm">
            Nie rozpoznano żadnych wpisów logu. Upewnij się, że wklejasz log w formacie
            Odoo (<code>data godzina pid LEVEL baza logger: treść</code>).
            ${s.unparsed_lines ? `Pominięto ${s.unparsed_lines} nierozpoznanych linii.` : ''}
        </div>`;
        return;
    }

    if (hint) {
        const tr = s.time_range || {};
        hint.textContent = `${s.parsed_entries} wpisów`
            + (tr.start ? ` · ${tr.start} → ${tr.end}` : '')
            + (s.unparsed_lines ? ` · ${s.unparsed_lines} nierozpoznanych` : '');
    }

    const parts = [];
    parts.push(renderLevelBar(s.by_level || {}));

    const rootCauses = s.root_causes || [];
    if (rootCauses.length) {
        const errs = s.errors || [];
        parts.push(`<div class="glass-card p-5 border border-red-500/30 bg-red-900/10 flex flex-col gap-3">
            <h2 class="text-lg font-semibold text-red-300 flex items-center gap-2">🎯 Root cause (bottom-up)</h2>
            ${rootCauses.map((rc) => {
                const e = errs.find((x) => x.root_cause === rc) || {};
                return `<div class="border border-red-500/20 rounded-lg p-3 bg-slate-900/40">
                    <div class="font-mono text-sm text-red-200 break-words">${_esc(rc)}</div>
                    <div class="text-xs text-slate-400 mt-1">
                        ${e.logger ? `<span class="text-slate-500">logger:</span> ${_esc(e.logger)} · ` : ''}
                        ${e.timestamp ? `<span class="text-slate-500">czas:</span> ${_esc(e.timestamp)}` : ''}
                    </div>
                </div>`;
            }).join('')}
        </div>`);
    }

    const httpErrors = s.http_errors || [];
    if (httpErrors.length) {
        parts.push(`<div class="glass-card p-5 flex flex-col gap-2">
            <h2 class="text-lg font-semibold text-amber-300 flex items-center gap-2">🌐 Błędy HTTP (${httpErrors.length})</h2>
            <div class="flex flex-col gap-1 text-sm font-mono">
                ${httpErrors.map((h) => `<div class="flex items-center gap-2">
                    <span class="px-2 py-0.5 rounded ${h.status >= 500 ? 'bg-red-500/20 text-red-300' : 'bg-amber-500/20 text-amber-300'} text-xs font-bold">${h.status}</span>
                    <span class="text-slate-400">${_esc(h.method)}</span>
                    <span class="text-slate-200 truncate" title="${_esc(h.path)}">${_esc(h.path)}</span>
                    <span class="text-slate-500 text-xs ml-auto">${_esc(h.timestamp || '')}</span>
                </div>`).join('')}
            </div>
        </div>`);
    }

    parts.push(renderEntries(entries));
    results.innerHTML = parts.join('');
}

function renderLevelBar(byLevel) {
    const order = ['CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG'];
    const chips = order
        .filter((lvl) => (byLevel[lvl] || 0) > 0)
        .map((lvl) => `<span class="px-3 py-1 rounded-full border text-xs font-semibold ${LEVEL_STYLE[lvl]}">${lvl}: ${byLevel[lvl]}</span>`)
        .join('');
    return `<div class="flex flex-wrap gap-2">${chips || '<span class="text-slate-500 text-sm">brak wpisów z poziomem</span>'}</div>`;
}

function renderEntries(entries) {
    const rows = entries.map((e) => {
        const badge = `<span class="px-2 py-0.5 rounded border text-[10px] font-bold ${LEVEL_STYLE[e.level] || LEVEL_STYLE.INFO}">${_esc(e.level)}</span>`;
        const tb = (e.traceback && e.traceback.length)
            ? `<pre class="mt-2 text-xs font-mono text-slate-400 bg-slate-950/60 border border-slate-800 rounded p-3 overflow-x-auto whitespace-pre">${_esc(e.traceback.join('\n'))}</pre>`
            : '';
        return `<div class="border-b border-slate-800/70 py-2">
            <div class="flex items-start gap-2 text-sm">
                ${badge}
                <span class="text-slate-500 text-xs whitespace-nowrap mt-0.5">${_esc(e.timestamp)}</span>
                <span class="text-indigo-300/80 text-xs whitespace-nowrap mt-0.5">${_esc(e.logger)}</span>
                <span class="text-slate-200 break-words">${_esc(e.message)}</span>
            </div>
            ${tb}
        </div>`;
    }).join('');

    return `<details class="glass-card p-5">
        <summary class="cursor-pointer text-slate-300 font-medium select-none">📜 Wszystkie wpisy (${entries.length})</summary>
        <div class="mt-3 flex flex-col">${rows}</div>
    </details>`;
}

// Eksponuj globalnie (onclick w HTML + spójność z window.App*).
window.parseLogs = parseLogs;
window.clearLogs = clearLogs;
