# 🚀 Sprint: [SmartMyOdoo-001] Zbudowanie SmartMyVault

> **Architekt:** /arch | **Tryb:** Sequential (Single-Dev /pol nadzór)
> **Data:** 2026-06-04 | **Bazuje na:** Planie Architektonicznym (Zero-Knowledge, Custom Python Vault)

---

## 📋 Sekcja A — Business Discovery & Rules

### Cel biznesowy
Eliminacja zewnętrznych rozwiązań SaaS (Infisical/Doppler) na rzecz stworzenia w 100% lokalnego i zaufanego menedżera sekretów (`SmartMyVault`). Vault musi wspierać *Zero-Knowledge AI Injection*, by ukrywać hasła przed agentami w terminalu i pamięci.

### Metryka sukcesu (DoD)
Uruchomienie kontenera Odoo za pomocą komendy `python vault.py run -- docker-compose up`, po której środowisko podniesie się poprawnie używając rozszyfrowanego w locie `MASTER_VAULT_DB_PASS`, bez ujawniania hasła w `stdout`.

### ⚖️ ZASADY SPRINTU — Podsumowanie dla Użytkownika

#### Zasada 1: SEQUENTIAL GATE (Bramka Sekwencyjna) 🔴
Każda faza musi zakończyć się bezwzględnym sukcesem. Kodowania w Fazie N+1 nie można zacząć, dopóki Faza N nie przejdzie testu Bramki.

#### Zasada 2: TDD FIRST / VALIDATION 🟠
Wymuszone testowanie "RED -> GREEN". Silnik wstrzykujący środowisko musi zostać pokryty testem przed aplikacją go na żywym Odoo.

#### Zasada 3: SCOPE ISOLATION 🔴
Wszystkie działania (Faza 1-3) będą prowadzone WYŁĄCZNIE w dedykowanym nowym folderze `smart_vault/`.

---

## 🧱 Sekcja B — Podział Zadań

### Graf zależności między Fazami

```text
┌──────────────────────────────────────┐
│  FAZA 1: Silnik Kryptograficzny      │
│  [PBKDF2 + AES (Fernet)]             │
│  [Tworzenie .enc i soli]             │
└──────────────┬───────────────────────┘
               │ ✅ BRAMKA: Poprawna inicjalizacja
               ▼
┌──────────────────────────────────────┐
│  FAZA 2: Human CLI (Zarządzanie)     │
│  [getpass, pyperclip (Schowek)]      │
│  [Komendy: add, list, copy]          │
└──────────────┬───────────────────────┘
               │ ✅ BRAMKA: Kopia sekretu w schowku
               ▼
┌──────────────────────────────────────┐
│  FAZA 3: AI Zero-Knowledge Wrapper   │
│  [subprocess.run + Wstrzyknięcie Env]│
└──────────────┬───────────────────────┘
               │ ✅ BRAMKA: Testowy skrypt py czyta env
               ▼
┌──────────────────────────────────────┐
│  FAZA 4: Integracja Odoo (Empty Shell│
│  [Modyfikacja docker-compose]        │
└──────────────────────────────────────┘
```

---

### Sekcja B1 — FAZA 1: Silnik Kryptograficzny

> **Trigger:** Stworzenie `vault.py`
> **📁 Scope:** `smart_vault/`

| # | Zadanie | DoD | Status |
|---|---------|-----|--------|
| 1.1 | Importy i struktura | Plik `vault.py` poprawnie importuje `cryptography`. | [x] |
| 1.2 | Logika PBKDF2 (Derive Key) | PIN `1111` + Salt = Bezpieczny klucz AES. | [x] |
| 1.3 | Logika `vault.py init` | Generuje pusty `master_vault.enc` i `salt.cfg`. | [x] |
| 1.4 | **BRAMKA:** Inicjalizacja skarbca | ✅ Skrypt startuje i tworzy odpowiednie pliki zabezpieczone na dysku. | [x] |

---

### Sekcja B2 — FAZA 2: Human CLI (Zarządzanie)

> **Trigger:** Zamknięta Faza 1
> **📁 Scope:** `smart_vault/`

| # | Zadanie | DoD | Status |
|---|---------|-----|--------|
| 2.1 | Komenda `add <key>` | Prosi (w ukryciu) o wartość i szyfruje w `.enc`. | [x] |
| 2.2 | Komenda `list` | Zwraca np. `[KLUCZE]: DB_PASS, STRIPE_API`. | [x] |
| 2.3 | Komenda `copy <key>` | Odszyfrowuje wartość i ładuje przez `pyperclip`. | [x] |
| 2.4 | Komenda `delete <key>` | (Dodatkowe: testowane E2E) Usuwa podany klucz ze skarbca. | [x] |
| 2.5 | **BRAMKA:** E2E Weryfikacja | ✅ Zbudowano testy E2E pokrywające wszystkie edge-case'y. | [x] |

---

### Sekcja B3 — FAZA 3: AI Zero-Knowledge Wrapper

> **Trigger:** Zamknięta Faza 2
> **📁 Scope:** `smart_vault/`

| # | Zadanie | DoD | Status |
|---|---------|-----|--------|
| 3.1 | Komenda `run <cmd>` | Wstrzykuje klucze z pamięci jako zmienne ENV do procesu potomnego. | [x] |
| 3.2 | Bezpieczeństwo | `os.environ` dziedziczone lokalnie (pod maską). | [x] |
| 3.3 | **BRAMKA:** Testowy skrypt py czyta env | ✅ Uruchomienie `python vault.py run "python test_env.py"` działa. | [x] |

---

### Sekcja B4 — FAZA 4: Integracja Odoo

> **Trigger:** Zamknięta Faza 3
> **📁 Scope:** Workspace główny (`templates/`)

| # | Zadanie | DoD | Status |
|---|---------|-----|--------|
| 4.1 | Czyszczenie `.env` Odoo | Modyfikacja `odoo_empty_shell.yml` by bazował w 100% na środowisku OS. | [ ] |
| 4.2 | Uruchomienie Dockera | Wykonanie `vault.py run -- docker-compose up -d`. | [ ] |
| 4.3 | **BRAMKA:** Audyt logów | ✅ Logi i środowisko operacyjne Odoo startuje bez wystawiania haseł na wierzch. | [ ] |

---

## ✅ Sekcja E — Finalna Weryfikacja

> Wykonuje użytkownik po zakończeniu wszystkich faz.

| # | Check (Core Pillars) | Komenda | Oczekiwany wynik |
|---|----------------------|---------|------------------|
| V1 | **Cryptography** | `python vault.py init` | Brak wycieków PINu. Salt stworzony. |
| V2 | **Zero-Knowledge AI** | `python vault.py run -- printenv` (lub odpowiednik Win) | Hasła widoczne dla procesu dziecka, niewidoczne w logach komendy AI. |
| V3 | **HITL Gates** | Zatrzymanie na prośbę o PIN | Agent musi przestać działać, czekając na wpisanie pinu. |
