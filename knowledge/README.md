# 🧠 knowledge/ — Wersjonowana baza wiedzy zespołu

> **Status:** Współdzielona (warstwa `__shared__`). Trafia do gita. Odtwarzana lokalnie do indeksu wektorowego przez `smartmyodoo seed`.

Ten folder jest **źródłem** wiedzy zespołowej (lekcje, instynkty, dokumenty
referencyjne). Zgodnie z [ADR-015](../docs/adr/ADR-015-Knowledge-As-Source-Secrets-Stay-Local.md)
oddzielamy **ŹRÓDŁO** (tekst w gicie, tutaj) od **INDEKSU** (LanceDB, budowany
lokalnie, gitignored).

## Jak to działa

```
knowledge/*.md  --(smartmyodoo seed --shared knowledge/)-->  LanceDB (lokalny, gitignored)
```

- Nowa osoba: `git clone` → `smartmyodoo seed --shared knowledge/` → ma ten sam
  baseline wiedzy współdzielonej.
- Wiedza **prywatna** (np. dane konkretnego klienta) NIE trafia tutaj — ląduje
  w warstwie prywatnej przez `--private <ścieżka> --workspace <id>`.

## Zasady (ART. 7 — Integralność i tagowanie wiedzy)

1. **Tylko tekst.** `.md` / `.txt`. Zero plików binarnych, zero sekretów
   (`.enc`, `.cfg`, `.key`, `.pem`, `.env`).
2. **Tagowanie.** Dodając plik wiedzy używaj tagów, np. `[#odoo, #orm, #security]`.
3. **Single Source of Truth.** Jedna informacja = jedno miejsce.
4. **NO SECRET IN ARTIFACT.** Nigdy nie wklejaj kluczy, haseł ani PII klientów.
   Sekrety zostają lokalnie w vault — patrz
   [docs/guides/sharing_knowledge_and_secrets.md](../docs/guides/sharing_knowledge_and_secrets.md).
