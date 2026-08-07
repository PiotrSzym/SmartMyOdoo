# -*- coding: utf-8 -*-
"""
fireflies_pull.py — pobieranie transkryptow spotkan z Fireflies.ai do folderow klientow.

Etap 1 (FF-01): narzedzie sesyjne "na zadanie" — zero zmian w runtime aplikacji.
  check                     test polaczenia (vault + API)
  list [--limit ...]        lista spotkan (metadane + dopasowanie klienta + status)
  fetch ID... [--klient X]  pobranie i zapis do Klienci/<klient>/04_Spotkania/RRRR-MM-DD-<slug>.md

Klucz API: sekret FIREFLIES_KEY w Skarbcu (pole api_key lub password — CLI `vault.py add`
zapisuje w password). PIN: ENV VAULT_PIN albo getpass. Zadna wartosc sekretu nie trafia
do stdout/logow. Tresc transkryptu nie jest drukowana — tylko sciezki plikow.
"""
import argparse
import getpass
import json
import os
import re
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

DEFAULT_BASE_DIR = Path(r"C:\od_zera_do_ai\myOdoo\Klienci")
MAP_FILENAME = "_fireflies_map.yml"
SECRET_NAME = "FIREFLIES_KEY"
LOCAL_TZ = ZoneInfo("Europe/Warsaw")
MEETINGS_SUBDIR = "04_Spotkania"


# --------------------------------------------------------------------------- vault

def get_api_key() -> str:
    from smartmyodoo.vault import vault  # import lokalny: nie wymagany dla --help

    pin = os.environ.get("VAULT_PIN") or getpass.getpass("PIN skarbca: ")
    vk = vault.get_vault_key_from_pin(pin, exit_on_fail=False)
    if vk is None:
        raise SystemExit("BLAD: niepoprawny PIN do skarbca.")
    data = vault.load_vault(vk)
    entry = data.get(SECRET_NAME) or {}
    api_key = entry.get("api_key") or entry.get("password")
    if not api_key:
        raise SystemExit(
            f"BLAD: brak sekretu '{SECRET_NAME}' w skarbcu (albo pusty). "
            f"Dodaj: python smartmyodoo/vault/vault.py add {SECRET_NAME}"
        )
    return api_key


# --------------------------------------------------------------------------- API

class FirefliesError(RuntimeError):
    pass


class FirefliesClient:
    """Minimalny klient GraphQL Fireflies.ai (adaptacja fireflies_connector)."""

    BASE_URL = "https://api.fireflies.ai/graphql"

    def __init__(self, api_key: str):
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    def _execute(self, query: str, variables: dict | None = None) -> dict:
        payload = {"query": query}
        if variables:
            payload["variables"] = variables
        try:
            resp = requests.post(self.BASE_URL, headers=self.headers, json=payload, timeout=30)
            resp.raise_for_status()
            data = resp.json()
        except requests.exceptions.RequestException as e:
            raise FirefliesError(f"HTTP: {e}") from e
        if "errors" in data:
            raise FirefliesError(f"GraphQL: {data['errors']}")
        return data.get("data", {})

    def list_transcripts(self, limit=20, skip=0, from_date=None, to_date=None) -> list:
        query = """
        query List($limit: Int, $skip: Int, $fromDate: DateTime, $toDate: DateTime) {
          transcripts(limit: $limit, skip: $skip, fromDate: $fromDate, toDate: $toDate) {
            id title date duration organizer_email participants
          }
        }"""
        variables = {"limit": min(int(limit), 50), "skip": int(skip)}
        if from_date:
            variables["fromDate"] = f"{from_date}T00:00:00.000Z"
        if to_date:
            variables["toDate"] = f"{to_date}T23:59:59.000Z"
        return self._execute(query, variables).get("transcripts") or []

    def get_transcript(self, transcript_id: str) -> dict:
        query = """
        query Transcript($id: String!) {
          transcript(id: $id) {
            id title date duration organizer_email participants
            summary { action_items overview }
            sentences { text speaker_name }
          }
        }"""
        return self._execute(query, {"id": transcript_id}).get("transcript") or {}


# --------------------------------------------------------------------------- helpers (czyste)

PL_MAP = str.maketrans("ąćęłńóśźżĄĆĘŁŃÓŚŹŻ", "acelnoszzACELNOSZZ")


def slugify(title: str, max_len: int = 60) -> str:
    s = (title or "spotkanie").translate(PL_MAP)
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
    return s[:max_len].rstrip("-") or "spotkanie"


def to_local_dt(raw) -> datetime:
    """Fireflies zwraca date jako epoch w MILISEKUNDACH (czasem ISO string)."""
    if isinstance(raw, (int, float)):
        return datetime.fromtimestamp(raw / 1000.0, tz=timezone.utc).astimezone(LOCAL_TZ)
    if isinstance(raw, str):
        try:
            return datetime.fromtimestamp(float(raw) / 1000.0, tz=timezone.utc).astimezone(LOCAL_TZ)
        except ValueError:
            return datetime.fromisoformat(raw.replace("Z", "+00:00")).astimezone(LOCAL_TZ)
    raise FirefliesError(f"Nieznany format daty: {type(raw)}")


def norm_participants(meeting: dict) -> list[str]:
    parts = meeting.get("participants") or []
    if isinstance(parts, str):
        parts = re.split(r"[,;\s]+", parts)
    emails = [p.strip().lower() for p in parts if p and "@" in str(p)]
    org = (meeting.get("organizer_email") or "").strip().lower()
    if org and org not in emails:
        emails.append(org)
    return emails


def load_map(base_dir: Path) -> dict:
    path = base_dir / MAP_FILENAME
    if not path.exists():
        return {"klienci": {}, "ignoruj_domeny": []}
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    data.setdefault("klienci", {})
    data.setdefault("ignoruj_domeny", [])
    return data


def match_client(meeting: dict, rules: dict) -> tuple[str | None, str]:
    """Kaskada email -> domena -> keyword. Zwraca (folder|None, poziom: e/d/k/?).
    Niejednoznacznosc (>=2 kandydatow na tym samym poziomie) => (None, '?')."""
    emails = norm_participants(meeting)
    ignored = {d.lower() for d in rules.get("ignoruj_domeny", [])}
    domains = {e.split("@", 1)[1] for e in emails} - ignored
    title = (meeting.get("title") or "").lower()

    for level, hit in (
        ("e", lambda cfg: bool(set(a.lower() for a in cfg.get("emails") or []) & set(emails))),
        ("d", lambda cfg: bool(set(d.lower() for d in cfg.get("domains") or []) & domains)),
        ("k", lambda cfg: any(k.lower() in title for k in cfg.get("keywords") or [])),
    ):
        candidates = [name for name, cfg in rules["klienci"].items() if hit(cfg or {})]
        if len(candidates) == 1:
            return candidates[0], level
        if len(candidates) > 1:
            return None, "?"
    return None, "?"


FRONT_ID_RE = re.compile(r"^fireflies_id:\s*(\S+)", re.MULTILINE)


def scan_existing_ids(base_dir: Path) -> dict[str, Path]:
    """Mapa fireflies_id -> sciezka pliku (skan Klienci/*/04_Spotkania/*.md)."""
    found: dict[str, Path] = {}
    for client_dir in sorted(base_dir.iterdir()):
        if not client_dir.is_dir() or client_dir.name.startswith("_"):
            continue
        meetings = client_dir / MEETINGS_SUBDIR
        if not meetings.is_dir():
            continue
        for md in meetings.glob("*.md"):
            try:
                head = md.read_text(encoding="utf-8", errors="replace")[:2000]
            except OSError:
                continue
            m = FRONT_ID_RE.search(head)
            if m:
                found[m.group(1)] = md
    return found


def render_note(t: dict, klient: str, match_info: str) -> str:
    dt = to_local_dt(t.get("date"))
    duration = int(round(float(t.get("duration") or 0)))
    emails = norm_participants(t)
    summary = t.get("summary") or {}
    overview = (summary.get("overview") or "").strip() or "_brak — podsumowanie niegotowe_"
    actions = summary.get("action_items") or ""
    if isinstance(actions, list):
        actions = "\n".join(f"- {a}" for a in actions if a)
    actions = (actions or "").strip() or "_brak_"

    # transkrypt: sklejanie kolejnych zdan tego samego mowcy w akapit
    lines, cur_speaker, buf = [], None, []
    for s in t.get("sentences") or []:
        speaker = (s.get("speaker_name") or "Nieznany").strip()
        text = (s.get("text") or "").strip()
        if not text:
            continue
        if speaker != cur_speaker and buf:
            lines.append(f"**{cur_speaker}:** {' '.join(buf)}")
            buf = []
        cur_speaker = speaker
        buf.append(text)
    if buf:
        lines.append(f"**{cur_speaker}:** {' '.join(buf)}")
    transcript = "\n\n".join(lines) or "_brak — transkrypt niegotowy (sprobuj pozniej z --force)_"

    return f"""---
klient: {klient}
typ: transkrypt
tags: [fireflies, spotkanie]
date: {dt:%Y-%m-%d}
status: raw
fireflies_id: {t['id']}
---

# {t.get('title') or 'Spotkanie'}

## Metadane
- **Data:** {dt:%Y-%m-%d %H:%M} (Europe/Warsaw)
- **Czas trwania:** {duration} min
- **Organizator:** {t.get('organizer_email') or '—'}
- **Uczestnicy:** {', '.join(emails) or '—'}
- **Dopasowanie klienta:** {match_info}

## Podsumowanie (Fireflies)
{overview}

## Action items
{actions}

## Transkrypt
{transcript}
"""


def write_note(base_dir: Path, klient: str, t: dict, content: str,
               existing: dict[str, Path], force: bool) -> Path:
    if force and t["id"] in existing:
        path = existing[t["id"]]  # nadpisz TEN SAM plik (bez duplikatu)
        path.write_text(content, encoding="utf-8", newline="\n")
        return path
    dt = to_local_dt(t.get("date"))
    meetings = base_dir / klient / MEETINGS_SUBDIR
    meetings.mkdir(parents=True, exist_ok=True)
    stem = f"{dt:%Y-%m-%d}-{slugify(t.get('title'))}"
    path, n = meetings / f"{stem}.md", 2
    while path.exists():  # kolizja nazwy z innym plikiem -> sufiks, nigdy nadpisanie
        path = meetings / f"{stem}-{n}.md"
        n += 1
    path.write_text(content, encoding="utf-8", newline="\n")
    return path


# --------------------------------------------------------------------------- komendy

def cmd_check(args):
    client = FirefliesClient(get_api_key())
    got = client.list_transcripts(limit=1)
    print(f"OK: polaczono z Fireflies API (proba listy: {len(got)} rekord/y).")


def cmd_list(args):
    base_dir = Path(args.base_dir)
    client = FirefliesClient(get_api_key())
    meetings = client.list_transcripts(args.limit, args.skip, args.from_date, args.to_date)
    rules = load_map(base_dir)
    existing = scan_existing_ids(base_dir)

    rows = []
    for i, m in enumerate(meetings, 1):
        folder, level = match_client(m, rules)
        rows.append({
            "nr": i,
            "data": f"{to_local_dt(m.get('date')):%Y-%m-%d %H:%M}",
            "czas_min": int(round(float(m.get("duration") or 0))),
            "id": m["id"],
            "tytul": (m.get("title") or "")[:45],
            "klient": f"{folder} ({level})" if folder else "?",
            "status": "POBRANE" if m["id"] in existing else "NOWE",
        })
    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=1))
        return
    if not rows:
        print("Brak spotkan w zadanym zakresie.")
        return
    fmt = "{nr:>3}  {data:16}  {czas_min:>4}m  {id:20}  {tytul:45}  {klient:35}  {status}"
    print("  #  DATA (Warszawa)   CZAS   ID                    "
          "TYTUL                                          KLIENT (dopasowanie)                 STATUS")
    for r in rows:
        print(fmt.format(**r))
    if any(r["klient"] == "?" for r in rows):
        print("\n'?' = brak/niejednoznaczne dopasowanie -> fetch z --klient <folder> "
              f"albo uzupelnij {base_dir / MAP_FILENAME}")


def cmd_fetch(args):
    base_dir = Path(args.base_dir)
    rules = load_map(base_dir)
    existing = scan_existing_ids(base_dir)

    if args.klient:
        target = base_dir / args.klient
        if args.klient.startswith("_") or not target.is_dir():
            raise SystemExit(f"BLAD: folder klienta '{args.klient}' nie istnieje w {base_dir} "
                             "(folderow nie tworzymy automatycznie).")

    client = FirefliesClient(get_api_key())
    failures = 0
    for tid in args.ids:
        if tid in existing and not args.force:
            print(f"POMINIETO {tid}: juz istnieje -> {existing[tid]}")
            continue
        t = client.get_transcript(tid)
        if not t:
            print(f"BLAD {tid}: API nie zwrocilo transkryptu.")
            failures += 1
            continue
        if args.klient:
            klient, match_info = args.klient, "reczne (--klient)"
        else:
            klient, level = match_client(t, rules)
            if not klient:
                print(f"NIEDOPASOWANE {tid} ('{(t.get('title') or '')[:40]}'): "
                      f"podaj --klient <folder> albo uzupelnij {base_dir / MAP_FILENAME}")
                failures += 1
                continue
            match_info = {"e": "email", "d": "domena", "k": "keyword"}[level] + " (_fireflies_map.yml)"
        content = render_note(t, klient, match_info)
        if args.dry_run:
            dt = to_local_dt(t.get("date"))
            target = base_dir / klient / MEETINGS_SUBDIR / f"{dt:%Y-%m-%d}-{slugify(t.get('title'))}.md"
            print(f"DRY-RUN {tid}: zapisalbym -> {target}")
            continue
        path = write_note(base_dir, klient, t, content, existing, args.force)
        existing[t["id"]] = path
        print(f"ZAPISANO {tid} -> {path}")
    if failures:
        raise SystemExit(1)


def main():
    p = argparse.ArgumentParser(description="Pobieranie transkryptow Fireflies do folderow klientow.")
    p.add_argument("--base-dir", default=str(DEFAULT_BASE_DIR),
                   help=f"katalog klientow (domyslnie {DEFAULT_BASE_DIR})")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("check", help="test polaczenia (vault + API)").set_defaults(func=cmd_check)

    pl = sub.add_parser("list", help="lista spotkan")
    pl.add_argument("--limit", type=int, default=20)
    pl.add_argument("--skip", type=int, default=0)
    pl.add_argument("--from", dest="from_date", metavar="RRRR-MM-DD")
    pl.add_argument("--to", dest="to_date", metavar="RRRR-MM-DD")
    pl.add_argument("--json", action="store_true")
    pl.set_defaults(func=cmd_list)

    pf = sub.add_parser("fetch", help="pobierz i zapisz transkrypty")
    pf.add_argument("ids", nargs="+", metavar="ID")
    pf.add_argument("--klient", help="folder klienta (nadpisuje matcher)")
    pf.add_argument("--dry-run", action="store_true")
    pf.add_argument("--force", action="store_true",
                    help="nadpisz istniejacy plik tego samego fireflies_id")
    pf.set_defaults(func=cmd_fetch)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
