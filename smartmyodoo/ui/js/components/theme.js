// js/components/theme.js
// Zarządzanie stanem i przełączaniem motywów (Jasny/Ciemny)

class ThemeEngine {
    constructor() {
        this.STORAGE_KEY = 'smo-theme';
        this.currentTheme = this._loadTheme();
        this._applyTheme(this.currentTheme);
    }

    _loadTheme() {
        return localStorage.getItem(this.STORAGE_KEY) || 'dark';
    }

    _applyTheme(themeName) {
        if (themeName === 'light') {
            document.documentElement.setAttribute('data-theme', 'light');
        } else {
            document.documentElement.removeAttribute('data-theme');
        }

        this._updateIcon(themeName);
    }

    _updateIcon(themeName) {
        const btn = document.getElementById('theme-toggle-btn');
        if (btn) {
            btn.innerHTML = themeName === 'light' ? '🌙' : '☀️';
            btn.title = themeName === 'light' ? 'Zmień na tryb ciemny' : 'Zmień na tryb jasny';
        }
    }

    toggle() {
        this.currentTheme = this.currentTheme === 'dark' ? 'light' : 'dark';
        localStorage.setItem(this.STORAGE_KEY, this.currentTheme);
        this._applyTheme(this.currentTheme);
    }

    getTheme() {
        return this.currentTheme;
    }
}

// Inicjalizacja zaraz po załadowaniu DOM
document.addEventListener('DOMContentLoaded', () => {
    window.AppTheme = new ThemeEngine();
});
