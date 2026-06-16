/**
 * JEDNO ŹRÓDŁO ikon UI (Lucide) — patrz ADR-006.
 * Mapowanie: stabilne ID (skill / program) → nazwa ikony Lucide.
 * Backendowe emoji (`/api/skills` -> icon) są tylko fallbackiem; prezentacja żyje TU.
 * Dodanie/zmiana ikony = jedna edycja w tym pliku.
 */

// 11 wyspecjalizowanych agentów (SkillName) → ikona Lucide
window.SKILL_ICONS = {
    ODOO_BUSINESS_ANALYST: "bar-chart-3",
    ODOO_DEVELOPER: "code",
    ODOO_DEVOPS_GITHUB: "git-branch",
    ODOO_SH_LOGS: "scroll-text",
    ODOO_AUDIT_HISTORY: "history",
    ODOO_CRUD: "database",
    ODOO_ETL_MANAGER: "package",
    FINANCIAL_AUDIT: "landmark",
    SECURITY_AUDIT: "shield-check",
    ODOO_API_EXPERT: "plug",
    MAGIC_FIX: "wand-2",
};

// Szybkie Programy (Skill Panel) → ikona Lucide
window.PROGRAM_ICONS = {
    P1: "database-zap",
    P2: "code",
    P3: "bug",
    P4: "settings-2",
    P5: "ruler",
};

// Helper: zwróć tag <i data-lucide> dla danego ID (fallback: emoji lub 'box')
window.skillIcon = function (id, fallbackEmoji) {
    const name = (window.SKILL_ICONS && window.SKILL_ICONS[id]) || null;
    if (name) return `<i data-lucide="${name}" class="w-5 h-5"></i>`;
    return fallbackEmoji || "📦";
};
window.programIcon = function (id) {
    const name = (window.PROGRAM_ICONS && window.PROGRAM_ICONS[id]) || "circle";
    return `<i data-lucide="${name}" class="w-7 h-7"></i>`;
};
