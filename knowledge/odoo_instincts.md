# Instynkty i lekcje — SmartMyOdoo

`[#odoo, #orm, #security, #api, #tdd, #python]`

> Współdzielona wiedza operacyjna zespołu. Źródło indeksu RAG (warstwa `__shared__`).
> Destylacja z procesu *Knowledge Harvest* (Odoo 16–19).

## Wersjonowanie API Odoo (CRITICAL)

- **Odoo 16:** ostatnia wersja z magicznymi krotkami ORM `(0, 0, {})` oraz
  atrybutem `attrs` w widokach XML.
- **Odoo 17 & 18:**
  - ZABRONIONE `attrs` w XML — zastępujemy wyrażeniami in-line, np.
    `invisible="state == 'draft'"`.
  - WYMAGANE `odoo.Command` do modyfikacji relacji; zakaz starych krotek
    numerycznych.
  - Nowe, obiektowe API zwracane przez `_read_group()`.
  - Tagi `<tree>` → `<list>`.
- **Odoo 19:**
  - Zewnętrzne integracje: zakaz starego JSON-RPC. Wymuszone **API JSON-2**
    (`/json2`) ze standardowymi kodami HTTP i Bearer Tokens.
  - `record._cr`, `record._context` oraz moduł `osv` — zdeprecjonowane.

## Bezpieczeństwo ORM i SQL

- Zawsze używaj wbudowanego ORM (`search`, `browse`, `write`, `create`).
  Surowy SQL tylko za zgodą `/arch`.
- Jeśli musisz `env.cr.execute` — ZAWSZE parametry (`%s`), ZERO f-stringów w
  zapytaniu (ochrona przed SQL Injection).
- `sudo()` wymaga pisemnego uzasadnienia i zgody `/sec`. Domyślnie prawa
  zalogowanego użytkownika.
- Webhooki Odoo <19: własne API zdejmujące domyślne `application/json` RPC
  wymaga `@http.route(..., type='http', auth="public", methods=['POST'], csrf=False)`.
- Proactive DB Checks: przed `.create()` w zewnętrznym API sprawdź duplikaty
  `.search(limit=1)` — blokuje `IntegrityError` PostgreSQL.

## Python (kontekst Odoo)

- Type hints obowiązkowe w metodach biznesowych i API (`-> dict`, `Optional[int]`).
- Synchroniczna natura ORM — trzymaj konwencję synchronicznych zapytań I/O.
- Parsowanie `__manifest__.py` czystym regexem — zakaz `eval()`.

## TDD i izolacja testów

- Każde zadanie startuje od czerwonego testu (Red → Green → Refactor).
- Testy LanceDB używają **tmp `db_path`** w fixture — NIGDY współdzielonego
  `.agents/lancedb_store` (izolacja, brak zanieczyszczenia globalnego store).
- Dockerized TDD Odoo: izolowany port `--http-port=8070` zapobiega kolizjom.

## Retrieval / RAG (S5.3)

- `degraded` sprawdzamy przez `is None` (NIE truthiness) — pusta tabela
  LanceDB ma `len == 0` i bywała mylona z brakiem połączenia.
- Degradacja > fabrykacja: brak retrievalu = zwróć `[]` / jawny komunikat,
  nigdy nie zmyślaj kontekstu.
- Dane partnerów/PII = warstwa prywatna `workspace_id`, NIGDY `"__shared__"`.
