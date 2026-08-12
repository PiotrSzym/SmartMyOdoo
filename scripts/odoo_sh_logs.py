#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""odoo_sh_logs.py — pobieranie logów build/deploy z Odoo.sh przez SSH (READ-ONLY).

Standalone CLI (wzorzec jak scripts/fireflies_pull.py). Rozszerza WIRE-01
(smartmyodoo/swarm/tools.py::_read_log_odoo_sh) o:
  - per-PROJEKT routing (mapa _odoo_sh_hosts.yml) — każdy Odoo.sh ma inny host SSH,
  - wszystkie 4 typy logów (odoo/update/install/pip),
  - zapis do pliku (pull).

BEZPIECZEŃSTWO (wzorzec WIRE-01/D3):
  - komenda jako argv-list, NIGDY shell=True, `lines` rzutowane na int,
  - `ssh -o BatchMode=yes` (bez interakcji), read-only `tail`,
  - klucz prywatny = plik lokalny (~/.ssh/...), NIE trzymany w repo,
  - host/user/ścieżka klucza NIE są echowane do stdout ani logów.

Mapa (routing, NIE sekret) w scripts/_odoo_sh_hosts.yml — poza repo (.gitignore):
  projects:
    <alias>:
      host: <z dashboardu Odoo.sh → branch → Connect/SSH>
      user: <build-id / user z connect-stringa>
      key_path: ~/.ssh/id_ed25519
      log_dir: ~/logs         # opcjonalnie, domyślnie ~/logs

Użycie:
  python scripts/odoo_sh_logs.py hosts
  python scripts/odoo_sh_logs.py check  <alias>
  python scripts/odoo_sh_logs.py logs   <alias> [--type odoo|update|install|pip|all] [-n 100]
  python scripts/odoo_sh_logs.py pull   <alias> [--type all] [-n 500]
"""
import argparse
import contextlib
import os
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("Brak PyYAML. Zainstaluj: pip install pyyaml")

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent
MAP_FILE = HERE / "_odoo_sh_hosts.yml"
SSH_TIMEOUT = 30
LOG_FILES = {"odoo": "odoo.log", "update": "update.log",
             "install": "install.log", "pip": "pip.log"}


def _load_map() -> dict:
    if not MAP_FILE.exists():
        sys.exit(f"Brak mapy hostów: {MAP_FILE}\n"
                 f"Utwórz ją wg wzoru z docstringu (scripts/_odoo_sh_hosts.example.yml).")
    data = yaml.safe_load(MAP_FILE.read_text(encoding="utf-8")) or {}
    return data.get("projects", {})


def _resolve(alias: str) -> dict:
    projects = _load_map()
    if alias not in projects:
        sys.exit(f"Nieznany alias '{alias}'. Dostępne: {', '.join(projects) or '(brak)'}")
    p = dict(projects[alias])
    for req in ("host", "user"):
        if not p.get(req):
            sys.exit(f"Alias '{alias}': brak wymaganego pola '{req}' w mapie.")
    # Klucz: albo ze Skarbca (key_from_vault: <nazwa_wpisu>), albo lokalny plik (key_path).
    if not p.get("key_from_vault") and not p.get("key_path"):
        sys.exit(f"Alias '{alias}': podaj 'key_from_vault' (nazwa wpisu w Skarbcu) lub 'key_path'.")
    if p.get("key_path"):
        p["key_path"] = os.path.expanduser(str(p["key_path"]))
        if not p.get("key_from_vault") and not Path(p["key_path"]).exists():
            sys.exit(f"Alias '{alias}': klucz SSH nie istnieje: {p['key_path']}")
    p.setdefault("log_dir", "~/logs")
    return p


@contextlib.contextmanager
def _key_file(p: dict):
    """Zwraca ścieżkę do klucza prywatnego. Gdy 'key_from_vault' — materializuje
    zawartość ze Skarbca do pliku tymczasowego 0600 i kasuje go po użyciu
    (klucz nie leży luźno na dysku ani nie idzie siecią)."""
    vault_key = p.get("key_from_vault")
    if not vault_key:
        yield p["key_path"]
        return
    # lazy import — vault dostępny gdy uruchamiane z repo
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    from smartmyodoo.vault import vault as _vault
    pin = os.environ.get("VAULT_PIN")
    if not pin:
        sys.exit("Brak VAULT_PIN — klucz jest w Skarbcu (key_from_vault). Ustaw VAULT_PIN=...")
    data = _vault.load_vault(_vault.get_vault_key_from_pin(pin, exit_on_fail=False))
    entry = data.get(vault_key)
    if not isinstance(entry, dict) or not entry.get("key"):
        sys.exit(f"Brak klucza prywatnego w Skarbcu pod '{vault_key}' (pole 'key').")
    fd, tmp = tempfile.mkstemp(prefix="odoosh_key_", suffix=".pem")
    try:
        os.write(fd, entry["key"].encode("utf-8"))
        os.close(fd)
        os.chmod(tmp, stat.S_IRUSR | stat.S_IWUSR)  # 0600 (best-effort na Win)
        yield tmp
    finally:
        with contextlib.suppress(OSError):
            os.remove(tmp)  # klucz nie zostaje na dysku


def _ssh_cmd(p: dict, key_path: str, remote_cmd: list[str]) -> list[str]:
    # argv-list; zero shell=True; klucz z pliku; bez interakcji.
    return ["ssh", "-i", key_path,
            "-o", "BatchMode=yes",
            "-o", "StrictHostKeyChecking=accept-new",
            "-o", f"ConnectTimeout={SSH_TIMEOUT}",
            f"{p['user']}@{p['host']}", *remote_cmd]


def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    # NIE logujemy cmd (zawiera host/user/ścieżkę klucza).
    return subprocess.run(cmd, capture_output=True, text=True, timeout=SSH_TIMEOUT + 5)


def cmd_hosts(_args):
    projects = _load_map()
    if not projects:
        print("(mapa pusta)")
        return
    print("Skonfigurowane projekty Odoo.sh:")
    for a, p in projects.items():
        # host/user pokazujemy (to NIE sekret), klucza NIE.
        print(f"  - {a}: {p.get('user','?')}@{p.get('host','?')}  log_dir={p.get('log_dir','~/logs')}")


def cmd_check(args):
    p = _resolve(args.alias)
    print(f"[{args.alias}] test połączenia SSH (read-only, `true`)...")
    try:
        with _key_file(p) as kp:
            res = _run(_ssh_cmd(p, kp, ["true"]))
    except (OSError, subprocess.SubprocessError):
        sys.exit("❌ SSH: nie udało się połączyć (proces/sieć).")
    if res.returncode == 0:
        print(f"✅ OK — połączono z {p['user']}@{p['host']}. Klucz działa.")
    else:
        # bez echa stderr w całości (mógłby zawierać host/user)
        first = (res.stderr or "").strip().splitlines()[:2]
        print("❌ SSH zwrócił błąd. Skrót diagnostyczny:")
        for ln in first:
            print("   " + ln)
        print("   → sprawdź: klucz zarejestrowany na Odoo.sh? rola Developer+ w projekcie? poprawny host/user z dashboardu?")


def _types(arg_type: str) -> list[str]:
    if arg_type == "all":
        return list(LOG_FILES)
    return [arg_type]


def _tail(p: dict, log_key: str, lines: int) -> tuple[int, str, str]:
    remote = f"{p['log_dir'].rstrip('/')}/{LOG_FILES[log_key]}"
    try:
        with _key_file(p) as kp:
            res = _run(_ssh_cmd(p, kp, ["tail", "-n", str(int(lines)), remote]))
    except (OSError, subprocess.SubprocessError):
        return 1, "", "połączenie/proces nieudane"
    return res.returncode, res.stdout, res.stderr


def cmd_logs(args):
    p = _resolve(args.alias)
    for t in _types(args.type):
        print(f"\n===== [{args.alias}] {LOG_FILES[t]} (ostatnie {args.n}) =====")
        rc, out, _err = _tail(p, t, args.n)
        if rc != 0:
            print(f"  ❌ nie pobrano {LOG_FILES[t]} (brak pliku lub błąd SSH)")
        else:
            print(out.rstrip() or "  (pusto)")


def cmd_pull(args):
    p = _resolve(args.alias)
    out_dir = HERE.parent / "_odoo_sh_logs" / args.alias
    out_dir.mkdir(parents=True, exist_ok=True)
    saved = []
    for t in _types(args.type):
        rc, out, _err = _tail(p, t, args.n)
        if rc == 0 and out:
            f = out_dir / LOG_FILES[t]
            f.write_text(out, encoding="utf-8")
            saved.append(str(f))
    if saved:
        print("ZAPISANO:")
        for s in saved:
            print("  " + s)
    else:
        print("❌ Nic nie pobrano (sprawdź `check` i uprawnienia).")


def main():
    ap = argparse.ArgumentParser(description="Odoo.sh logi przez SSH (read-only)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("hosts").set_defaults(func=cmd_hosts)
    c = sub.add_parser("check"); c.add_argument("alias"); c.set_defaults(func=cmd_check)
    for name in ("logs", "pull"):
        s = sub.add_parser(name)
        s.add_argument("alias")
        s.add_argument("--type", choices=[*LOG_FILES, "all"], default="odoo")
        s.add_argument("-n", type=int, default=100 if name == "logs" else 500)
        s.set_defaults(func=cmd_logs if name == "logs" else cmd_pull)
    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
