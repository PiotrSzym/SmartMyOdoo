---
name: fireflies-transcripts
description: Pobieranie na żądanie transkryptów spotkań z Fireflies.ai i układanie ich chronologicznie w folderach klientów myOdoo (Klienci\<klient>\04_Spotkania). Użyj gdy właściciel mówi "pobierz transkrypt", "fireflies", "spotkania z fireflies", "transkrypcja spotkania", "zaciągnij spotkanie". Skrypt scripts/fireflies_pull.py + sekret FIREFLIES_KEY w Skarbcu + mapa _fireflies_map.yml.
---

# fireflies-transcripts — transkrypty Fireflies → foldery klientów

Cel: na żądanie właściciela pobrać wskazane spotkania z Fireflies.ai i zapisać jako
`C:\od_zera_do_ai\myOdoo\Klienci\<klient>\04_Spotkania\RRRR-MM-DD-<slug>.md`
(front-matter YAML + podsumowanie + action items + pełny transkrypt; `status: raw`).

## Wymagania wstępne
- Sekret **`FIREFLIES_KEY`** w Skarbcu (dodanie: `python smartmyodoo/vault/vault.py add FIREFLIES_KEY`).
  ⚠ CLI `add` zapisuje wartość w polu `password` (nie `api_key`) — skrypt czyta kaskadą `api_key|password`, nie „naprawiaj" tego.
- PIN: ENV `VAULT_PIN` (per sesja) albo skrypt zapyta getpass. Nigdy nie wpisuj PIN/klucza do kodu ani logów.
- Mapa dopasowań: `C:\od_zera_do_ai\myOdoo\Klienci\_fireflies_map.yml` (kaskada email→domena→keyword; plik lokalny, poza repo).

## Przepływ sesyjny (tryb „jak ci powiem")
```bash
cd C:\od_zera_do_ai\SmartMyOdoo
python scripts/fireflies_pull.py check                 # test vault + API
python scripts/fireflies_pull.py list --limit 20       # tabela: nr, data, ID, tytuł, KLIENT(e/d/k lub ?), NOWE/POBRANE
# pokaż tabelę właścicielowi → właściciel wskazuje numery/ID →
python scripts/fireflies_pull.py fetch <ID> [<ID>...]  # zapis; drukuje TYLKO ścieżki plików
```
- `list --json` — gdy potrzebujesz sparsować wynik maszynowo.
- Filtry: `--from RRRR-MM-DD --to RRRR-MM-DD --skip N` (limit API: 50/zapytanie, bez pętli automatycznych — dzienne limity Fireflies).
- **Klient `?` (brak/niejednoznaczne dopasowanie):** `fetch` zatrzyma się z komunikatem. ZAPYTAJ właściciela, do którego klienta należy spotkanie, i powtórz `fetch <ID> --klient <folder>`. Przy okazji zaproponuj uzupełnienie `_fireflies_map.yml` (emails/domains/keywords), żeby następnym razem dopasowało się samo.
- `fetch --dry-run` — pokaż docelową ścieżkę bez zapisu (używaj przy pierwszym przebiegu z nowym klientem).

## Idempotencja / ciągłość
- Źródło prawdy: `fireflies_id:` we front-matterze — ponowny `fetch` tego samego ID → `POMINIETO` (w `list` status `POBRANE`).
- `--force` nadpisuje TEN SAM plik (po ID, nie tworzy duplikatu) — używaj TYLKO na wyraźne polecenie albo do dociągnięcia transkryptu, który przy pierwszym pobraniu był niegotowy (placeholdery „_brak — niegotowe_").
- Chronologia = prefiks datowy w nazwie pliku; kolizja nazw → automatyczny sufiks `-2` (nigdy nadpisanie cudzej notatki).

## Zasady twarde
1. **NIE wklejaj treści transkryptu do odpowiedzi** bez wyraźnej prośby (PII klientów; pliki zostają lokalnie w folderach klientów).
2. **NIE twórz folderów klientów** — `fetch --klient` waliduje, że folder istnieje; nowy klient = decyzja właściciela.
3. Sekrety: nazwy tak, wartości nigdy (dotyczy też komunikatów o błędach).
4. Opracowanie transkryptu w notatkę (decyzje/next steps) — TYLKO na prośbę właściciela, jako osobny plik lub edycja `status: raw → draft`.

## Troubleshooting
- `BLAD: brak sekretu 'FIREFLIES_KEY'` → Krok „Wymagania wstępne" (dodaj sekret).
- Świeże spotkanie: `summary`/`sentences` mogą być puste → plik z placeholderami; dociągnij później `fetch <ID> --force`.
- Daty: API zwraca epoch w **milisekundach** UTC; skrypt konwertuje na Europe/Warsaw — nie „poprawiaj" dat ręcznie.
- GraphQL error o limitach → odczekaj / zmniejsz `--limit`; nie pętluj.

## Pochodzenie (Etap 1, FF-01, 2026-08-07)
Adaptacja `FirefliesClient` z modułu Odoo `fireflies_connector` (Smart_odoo\addons_myodoo); matcher ORM-owy NIEprzeniesiony — zamiast niego lokalna kaskada na `_fireflies_map.yml`. Etap 2 (produktowy: CredentialType.EXTERNAL_API + skill roju) = osobna decyzja sprintowa.
