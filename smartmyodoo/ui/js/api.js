// js/api.js
// UX-10 (T1): Centralny helper HTTP dla całego UI (vanilla-JS, ADR-006 — zero zależności).
//
// Problem: ~15 miejsc ręcznie budowało `fetch(url, {headers:{Authorization:'Bearer '+token}})`.
// Każde z osobna czytało token z AppStore i dublowało logikę nagłówka. Trudne do audytu
// (gdzie wstrzykiwany jest token?) i podatne na błędy (literówka, brak nagłówka).
//
// Rozwiązanie: `authFetch(url, opts)` — jeden punkt, w którym dokładamy
// `Authorization: Bearer <authToken>` z AppStore. Zachowuje semantykę natywnego `fetch`
// (zwraca Response, przyjmuje te same opcje), więc migracja to podmiana nazwy.
//
// BEZPIECZEŃSTWO (Sekcja D): helper NIE loguje tokenu (żaden console.* z tokenem),
// token NADAL żyje tylko w pamięci AppStore (nie localStorage — STORE_PERSIST_FIELDS).

/**
 * Fetch z automatycznym nagłówkiem `Authorization: Bearer <authToken>`.
 *
 * Token pobierany jest z `window.AppStore` w momencie wywołania (nie cache'owany),
 * więc po zalogowaniu kolejne wywołania używają świeżego tokenu. Istniejące nagłówki
 * z `opts.headers` są zachowane; gdy wywołujący poda własny `Authorization`, ma on
 * pierwszeństwo (nie nadpisujemy świadomej decyzji).
 *
 * @param {string} url Adres żądania (jak w natywnym fetch).
 * @param {RequestInit} [opts={}] Opcje fetch (method, body, headers, ...).
 * @returns {Promise<Response>} Surowy Response — obsługa statusu (np. 401) po stronie wołającego.
 */
function authFetch(url, opts = {}) {
    const token = (window.AppStore && window.AppStore.getState().authToken) || '';

    // Scal nagłówki: domyślny Bearer + nagłówki wołającego (te drugie wygrywają).
    const headers = {
        'Authorization': `Bearer ${token}`,
        ...(opts.headers || {}),
    };

    return fetch(url, { ...opts, headers });
}

// Eksponuj globalnie (wzorzec window.App* z pozostałych modułów UI).
window.authFetch = authFetch;
