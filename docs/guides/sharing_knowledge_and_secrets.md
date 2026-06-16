# 🤝 Współdzielenie wiedzy i poświadczeń

> **Decyzja architektoniczna:** [ADR-015 — Knowledge-as-Source / Secrets-Stay-Local](../adr/ADR-015-Knowledge-As-Source-Secrets-Stay-Local.md)
> **Zasada nadrzędna:** WIEDZA jedzie jako tekst w gicie; INDEKS wektorowy i SEKRETY zostają lokalne.

Gdy przekazujesz SmartMyOdoo innej osobie lub zespołowi (`git clone` + Docker),
ten przewodnik wyjaśnia **co jest współdzielone, a co prywatne**.

---

## 1. Wiedza zespołowa = tekst w gicie (`knowledge/`)

Lekcje, instynkty i dokumenty referencyjne trzymamy w wersjonowanym folderze
[`knowledge/`](../../knowledge/). Trafiają do repozytorium jako **źródło**.
Indeks wektorowy (LanceDB) jest **pochodny** i budowany lokalnie — pozostaje
gitignored, nigdy nie trafia do repo ani obrazu Docker.

**Nowa osoba po klonie:**

```bash
git clone <repo> && cd SmartMyOdoo
pip install -e .
python -m smartmyodoo seed --shared knowledge/   # buduje lokalny indeks shared
```

Efekt: ten sam baseline wiedzy współdzielonej, bez kopiowania binariów.

### Warstwy: shared vs private

Każdy rekord w bazie wiedzy ma `workspace_id`:

- **`__shared__`** — warstwa współdzielona (domyślna dla `knowledge/`).
- **realny `workspace_id`** — warstwa prywatna (np. dane konkretnego klienta).

```bash
# Wiedza prywatna konkretnego workspace (NIE trafia do shared):
python -m smartmyodoo seed --private /sciezka/do/danych --workspace client_a
```

`search(workspace=A)` zwraca **shared ∪ A**, a **NIGDY** prywatne dane innego
workspace `B`. Dane partnerów/PII należą zawsze do warstwy prywatnej — nigdy do
`__shared__`.

---

## 2. Sekrety (vault) — 3 ścieżki

Vault (klucze Odoo/LLM) jest **lokalny, szyfrowany** (Fernet + PBKDF2). Pliki
`*.enc`/`*.cfg` są gitignored — aplikacja shipuje się z **pustym** vaultem
(każdy robi `init`). **Nigdy nie kopiuj plików `.enc` do gita ani obrazu Docker.**

### Ścieżka A — zespół: każdy własny vault (zalecane)

Każda osoba inicjalizuje własny skarbiec i wpisuje własne poświadczenia:

```bash
python -m smartmyodoo.vault.vault init
python -m smartmyodoo.vault.vault add ODOO
```

Brak współdzielenia plików vault. Najbezpieczniejsze domyślne podejście.

### Ścieżka B — migracja TEJ SAMEJ osoby (export/import)

Przenosisz **własne** sekrety na nową maszynę. Eksport to **zaszyfrowany,
samowystarczalny blob** chroniony PIN-em (klucz wyprowadzany z PIN, nie z
plików lokalnych):

```bash
# Stara maszyna:
python -m smartmyodoo.vault.vault export vault_backup.enc

# Nowa maszyna (ten sam PIN, przekazany SOBIE osobnym bezpiecznym kanałem):
python -m smartmyodoo.vault.vault import vault_backup.enc
```

> ⚠️ **To NIE jest mechanizm współdzielenia zespołowego.** Blob i PIN przekazujesz
> wyłącznie samemu sobie. Nie wysyłaj go współpracownikom.

### Ścieżka C — organizacja: menedżer sekretów

Zespół, który **musi** współdzielić te same klucze, używa zewnętrznego
**menedżera sekretów** — nie plików `.enc`:

- 1Password / Bitwarden (zespołowe sejfy)
- HashiCorp Vault
- Cloud KMS (AWS/GCP/Azure)

Świadomie **nie budujemy** własnego serwera sekretów (poza scope, ryzyko
bezpieczeństwa — patrz ADR-015).

---

## ✅ Czego NIGDY nie robimy

- ❌ Kopiowania `*.enc` / `*.cfg` / `vault_data.enc` do gita lub obrazu Docker.
- ❌ Wpychania binarnego indeksu LanceDB do repo (jest pochodny — odbuduj `seed`).
- ❌ Umieszczania PII klientów w warstwie `__shared__`.
- ❌ Przesyłania bloba `vault export` współpracownikom (to migracja JEDNEJ osoby).
