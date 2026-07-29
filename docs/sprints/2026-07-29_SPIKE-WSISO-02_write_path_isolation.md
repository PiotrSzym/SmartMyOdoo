---
spike_id: "WSISO-02"
workspace: "SmartMyOdoo"
status: "📋 Draft dla /arch (PRE-sprint)"
created: 2026-07-29
prefix: "WSISO"
complexity: 7
parent: "WSISO-01 (cee896b) + guard (864032d)"
tags: ["security", "workspace-isolation", "odoo-auth", "write-path", "cross-client", "sandbox", "arch-input"]
---

# 📋 SPIKE WSISO-02 — Pełna izolacja poświadczeń Odoo na ŚCIEŻCE ZAPISU (pipeline/sandbox)

> Wejście dla /arch. WSISO-01 (`cee896b`) zamknął izolację ODCZYTU; guard (`864032d`) doraźnie zamknął cichy cross-client LEAK na zapisie. Ten spike zbiera fakty i decyzje do podjęcia dla PEŁNEJ izolacji write-path.

## 0. Problem (1 zdanie)
Ścieżka zapisu/wykonania (pipeline + sandbox) buduje połączenie Odoo z ENV `ODOO_URL` / generycznego sekretu `ODOO` — **BEZ typowanego sekretu per-workspace** — więc nawet po guardzie zapisy NIE trafiają do właściwej instancji workspace (typowy `{ws}_ODOO`/ODOO_DATA z vaultu jest ignorowany).

## 1. Fakty (dowód z kodu + live, 2026-07-29)
| # | Miejsce | Dowód | Skutek |
|---|---------|-------|--------|
| W1 | POST `/api/pipeline/run` | `chat.py:466-472` — `odoo_url=os.environ["ODOO_URL"]`, `odoo_secret=vault_data.get("ODOO", ...)` | zapis na ENV/generic, nie na sekret ws |
| W2 | WS `/api/chat/stream` (use_pipeline) | `chat.py:677-705` — identyczny wzorzec ENV/generic | to samo w streamie |
| W3 | Sandbox (klon scratchpad DB) | `sandbox.py:31-35` — `os.environ["ODOO_URL"]` + `ODOO_MASTER_PASSWORD` | master-password globalny, nie per-ws |
| W4 | Guard obecny (`864032d`) | `_resolve_write_odoo_target` kieruje url/db na sekret ws LUB blokuje; ale master-password NADAL z ENV | guard zamyka LEAK, nie robi pełnej izolacji |

**Dowód live (`[ODOO-TRACK]`, PIN 1111):**
- `write ws=grfood host=None db=None src=BLOCKED` → guard OK (brak leaku)
- `write ws=default host=localhost db=odoo_prod src=ENV` → default zapisuje na **localhost:8069 z ENV**, a NIE na sekret vaultu „myodoo Test"/„default_ODOO" (chmura). To pokazuje rozjazd write-path ↔ vault.

**Vault (stan):** typowane sekrety Odoo istnieją per-workspace (`default`=4, `myodooTest`=2, `grfood`=0) — pipeline ich nie używa.

## 2. Niezmiennik do wymuszenia (spójny z WSISO-01)
> Zapis/wykonanie dla workspace X łączy się WYŁĄCZNIE z instancją Odoo skonfigurowaną w typowanym sekrecie X (`{X}_ODOO`/ODOO_DATA). `default` — analogicznie (jego sekret; ENV tylko jako świadomy fallback `vault run`). Brak sekretu dla wybranego nie-default → głośny błąd (już robi guard). NIGDY instancja/master-password innego workspace.

## 3. Pytania/decyzje DLA /arch (to jest sedno spike'u)
- **D-A: master-password per-workspace?** Sandbox klonuje scratchpad DB — wymaga master-password Odoo. Czy `ODOO_DATA` per-ws niesie też master-password, czy osobny typowany sekret `{ws}_ODOO_MASTER`? (dziś globalny ENV `ODOO_MASTER_PASSWORD`).
- **D-B: semantyka sandboxa dla instancji chmurowej.** Klon bazy (scratchpad) na Odoo.sh/chmurze bywa niemożliwy/niebezpieczny per-tenant. Czy sandbox jest N/A dla nie-lokalnych instancji → write bez klonu + inny mechanizm rollbacku (Credit Note / dry-run)?
- **D-C: źródło url/db/login.** Ujednolicić z resolverem WSISO-01 (`resolve_credential(ODOO_DATA, ws, allow_default_fallback=False)`) zamiast generycznego `ODOO`/ENV — czy `default` też przechodzi na typowany sekret (zmiana zachowania: dziś localhost ENV)?
- **D-D: OdooDBManager vs OdooClient.** Write-path używa `OdooDBManager(url, master_pwd)`, read-path `OdooClient` (ContextVar). Czy zunifikować budowę połączenia (jedno źródło prawdy), czy zostawić dwa i tylko wyrównać źródło creds?
- **D-E: migracja.** Setupy liczące na ENV `ODOO_URL` dla zapisu (dziś localhost) zobaczą zmianę. Nota migracyjna + fallback dla `default`?

## 4. Poza zakresem (proponowane)
Zmiana silnika sandbox/rollback (osobny track), multi-instancja per skill, provisioning kluczy (AZURE-01).

## 5. Gotowe klocki do reużycia
- `_resolve_write_odoo_target` (`chat.py`) — już kieruje url/db na sekret ws / blokuje; rozszerzyć o master-password.
- `resolve_credential(..., allow_default_fallback=False)` (`vault/resolver.py`) — kanoniczny wybór typowanego sekretu.
- `OdooWorkspaceUnconfigured` + `classify_odoo_error` — sanityzowany błąd.
- `[ODOO-TRACK]` log — gotowa weryfikacja live per-workspace.

## 6. Echo audytu #2
A-1 (staging→prod przy dual-instance) — write-path izolacja domyka ten sam wektor na zapisie. Priorytet: cross-client WRITE (wyższe ryzyko niż odczyt).
