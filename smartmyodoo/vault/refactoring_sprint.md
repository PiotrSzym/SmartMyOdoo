# 🚀 Sprint: [SmartMyOdoo-003] Refactoring & Code Hardening

> **Architekt:** /arch | **Tryb:** Sequential (Single-Dev /qa nadzór)
> **Data:** 2026-06-04 | **Bazuje na:** QA Report & Analiza Architektoniczna (Python Best Practices)

---

## 📋 Sekcja A — Business Discovery & Rules

### Cel biznesowy
Wyeliminowanie **3 błędów krytycznych** (wyciek kryptografii do warstwy HTTP, ogólne `except Exception`, `sys.exit` zabijający serwer) oraz **5 naruszeń architektonicznych** (duplikacja kodu CLI 5×, brakujące type hinty, leniwe importy). Usunięcie plików-sierot z poprzednich iteracji. Kod po sprincie musi spełniać standard PEP 8, Separation of Concerns i być odporny na regresję dzięki rozszerzonym testom.

### Metryka sukcesu (DoD)
1. Żadna funkcja w `vault.py` nie wywołuje `sys.exit()` poza `main()` i interaktywnymi komendami CLI.
2. Warstwa API (`vault_server.py`) nie importuje ani nie używa bezpośrednio `cryptography.fernet.Fernet`.
3. Pełny suite testów (`test_vault.py` + `test_vault_server.py`) przechodzi na zielono z pokryciem scenariuszy błędnych (401, 403, złe klucze).
4. Brak plików-sierot w folderze `smart_vault/`.

### ⚖️ ZASADY SPRINTU

#### Zasada 1: SEQUENTIAL GATE (Bramka Sekwencyjna) 🔴
Najpierw rdzeń (`vault.py`), potem serwer API, potem higiena, na końcu testy. Nie modyfikujemy serwera dopóki rdzeń nie jest gotowy.

#### Zasada 2: TDD FIRST / VALIDATION 🟠
Istniejące testy `test_vault.py` i `test_vault_server.py` MUSZĄ przechodzić po KAŻDEJ fazie. Testy rozszerzamy w Fazie 10.

#### Zasada 3: SCOPE ISOLATION 🔴
Zmiany WYŁĄCZNIE w `smart_vault/`. Zero modyfikacji w reszcie workspace'u.

---

## 🧱 Sekcja B — Podział Zadań

### Graf zależności między Fazami

```text
┌──────────────────────────────────────┐
│  FAZA 7: Rdzeń Kryptograficzny       │
│  [VaultDecryptionError]              │
│  [update_pin(), _cli_auth()]         │
│  [Zawężenie except, Type Hinty]      │
└──────────────┬───────────────────────┘
               │ ✅ BRAMKA: Istniejące testy GREEN
               ▼
┌──────────────────────────────────────┐
│  FAZA 8: Serwer API (Cleanup)        │
│  [Usunięcie Fernet z vault_server]   │
│  [vault.update_pin() zamiast kodu]   │
│  [Obsługa VaultDecryptionError]      │
└──────────────┬───────────────────────┘
               │ ✅ BRAMKA: API testy GREEN
               ▼
┌──────────────────────────────────────┐
│  FAZA 9: Higiena Repozytorium        │
│  [Usunięcie master_vault.enc]        │
│  [Usunięcie salt.cfg]                │
└──────────────┬───────────────────────┘
               │ ✅ BRAMKA: Brak sierot w ls
               ▼
┌──────────────────────────────────────┐
│  FAZA 10: Rozszerzenie Testów        │
│  [update_pin, VaultDecryptionError]  │
│  [API 401/403 edge-case'y]           │
└──────────────────────────────────────┘
```

---

### Sekcja B1 — FAZA 7: Rdzeń Kryptograficzny (`vault.py`)

> **Trigger:** Zatwierdzenie Sprintu przez użytkownika
> **📁 Scope:** `smart_vault/vault.py`

| # | Zadanie | DoD | Status |
|---|---------|-----|--------|
| 7.1 | Klasa `VaultDecryptionError(Exception)` | Nowy typ wyjątku zdefiniowany na górze pliku. | [ ] |
| 7.2 | `load_vault()` → `raise VaultDecryptionError` zamiast `sys.exit(1)` | Funkcja NIGDY nie zabija procesu. CLI opakowuje to w try/except. | [ ] |
| 7.3 | Zawęzić `except Exception` w `get_vault_key_from_pin/master` | Łapie tylko `cryptography.fernet.InvalidToken` i `ValueError`. | [ ] |
| 7.4 | Nowa funkcja `update_pin(vk: bytes, new_pin: str) -> None` | Przeniesiona logika zmiany PINu z `vault_server.py`. | [ ] |
| 7.5 | Nowa funkcja `_cli_auth() -> tuple[bytes, dict]` | Eliminuje duplikat `getpass → get_key → load_vault` z 5 komend CLI. | [ ] |
| 7.6 | Refactor CLI commands → `_cli_auth()` | `add_secret`, `copy_secret`, `delete_secret`, `restore_secret`, `list_secrets` używają helpera. | [ ] |
| 7.7 | Dodać pełne Type Hinty | Wszystkie publiczne funkcje mają `-> ReturnType`. | [ ] |
| 7.8 | **BRAMKA:** Istniejące testy GREEN | ✅ `python -m unittest test_vault.py` → 8/8 OK. | [ ] |

---

### Sekcja B2 — FAZA 8: Serwer API (`vault_server.py`)

> **Trigger:** Zamknięta Faza 7
> **📁 Scope:** `smart_vault/vault_server.py`

| # | Zadanie | DoD | Status |
|---|---------|-----|--------|
| 8.1 | Przenieść importy na górę pliku | Zero `import` wewnątrz ciał funkcji. PEP 8 compliance. | [ ] |
| 8.2 | `/api/change-pin` → `vault.update_pin()` | Usunięte bezpośrednie wywołania `Fernet`, `os.urandom` z kodu HTTP. | [ ] |
| 8.3 | Obsługa `VaultDecryptionError` | Endpointy CRUD łapią wyjątek i zwracają HTTP 500 zamiast `sys.exit`. | [ ] |
| 8.4 | Type Hinty w `get_auth_key()` | `-> tuple[bytes | None, str | None]` | [ ] |
| 8.5 | **BRAMKA:** API testy GREEN | ✅ `python -m unittest test_vault_server.py` → OK. | [ ] |

---

### Sekcja B3 — FAZA 9: Higiena Repozytorium

> **Trigger:** Zamknięta Faza 8
> **📁 Scope:** `smart_vault/`

| # | Zadanie | DoD | Status |
|---|---------|-----|--------|
| 9.1 | Usunąć `master_vault.enc` | Plik-sierota z Fazy 1 — nie referencjonowany w żadnym kodzie. | [ ] |
| 9.2 | Usunąć `salt.cfg` | Plik-sierota — zastąpiony przez `pin_salt.cfg` + `master_salt.cfg`. | [ ] |
| 9.3 | **BRAMKA:** Czysty listing | ✅ Brak plików nie-referencjonowanych w folderze. | [ ] |

---

### Sekcja B4 — FAZA 10: Rozszerzenie Testów

> **Trigger:** Zamknięta Faza 9
> **📁 Scope:** `smart_vault/test_vault.py`, `smart_vault/test_vault_server.py`

| # | Zadanie | DoD | Status |
|---|---------|-----|--------|
| 10.1 | Test `vault.update_pin()` | Nowy PIN deszyfruje ten sam Vault Key co stary. | [ ] |
| 10.2 | Test `load_vault()` z błędnym kluczem | Rzuca `VaultDecryptionError`, NIE wywołuje `sys.exit`. | [ ] |
| 10.3 | Test API: 401 Unauthorized | Zapytanie bez headera `Authorization` → 401. | [ ] |
| 10.4 | Test API: 403 Change PIN non-admin | Zapytanie z PINem (rola `user`) na `/api/change-pin` → 403. | [ ] |
| 10.5 | **BRAMKA:** Full Suite GREEN | ✅ `python -m unittest test_vault.py test_vault_server.py -v` → ALL OK. | [ ] |

---

## ✅ Sekcja E — Finalna Weryfikacja

> Wykonuje użytkownik po zakończeniu wszystkich faz.

| # | Check (Core Pillars) | Komenda | Oczekiwany wynik |
|---|----------------------|---------|------------------|
| V1 | **Separation of Concerns** | `grep "Fernet" vault_server.py` | Zero wyników — kryptografia WYŁĄCZNIE w `vault.py`. |
| V2 | **No sys.exit in library** | `grep "sys.exit" vault.py` | Występuje TYLKO w `main()` i interaktywnych komendach CLI (nie w `load_vault`, `get_secrets`). |
| V3 | **Exception Specificity** | `grep "except Exception" vault.py` | Zero wyników — wszystkie `except` są specyficzne. |
| V4 | **Full Test Suite** | `python -m unittest test_vault.py test_vault_server.py -v` | 100% GREEN, zero FAIL. |
| V5 | **GUI Smoke Test** | `python vault.py gui` → przeglądarka | Dodanie, usunięcie, kosz, przywrócenie — wszystko działa. |
