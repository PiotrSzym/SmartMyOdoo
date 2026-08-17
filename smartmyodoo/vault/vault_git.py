# -*- coding: utf-8 -*-
"""KEY-03: konsument tokenów VCS ze Skarbca — PIN pytany PER WYWOŁANIE.

Skarbiec jest domyślnym magazynem sekretów; token VCS (GitHub/GitLab) wstrzykiwany
jest TYLKO do jednego podprocesu (git/gh) na czas jednej komendy. PIN podajesz w
natywnym oknie za każdym razem — nigdy z ENV, argumentów, logów ani kontekstu AI.

Użycie:
    python -m smartmyodoo.vault.vault_git gh repo clone myOdoo-pl/Moduly-3p
    python -m smartmyodoo.vault.vault_git git clone https://github.com/myOdoo-pl/Moduly-3p dst
    python -m smartmyodoo.vault.vault_git run -- git -C dst pull
    python -m smartmyodoo.vault.vault_git import-gh --user ps-myodoo [--logout]

Bezpieczeństwo:
- PIN wyłącznie z natywnego okna (tkinter) lub getpass — NIGDY z ENV/argv.
- Token nie trafia do argv: dla `git` przez GIT_CONFIG_* + credential helper czytający
  $GH_TOKEN; dla `gh` przez zmienną GH_TOKEN. Wartości nie są wypisywane.
"""
import os
import sys
import getpass
import argparse
import subprocess

# repo root na PYTHONPATH (…/smartmyodoo/vault/vault_git.py -> repo root = 2 katalogi wyżej)
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from smartmyodoo.vault.vault import (  # noqa: E402
    get_vault_key_from_pin,
    load_vault,
    save_vault,
)
from smartmyodoo.vault.resolver import resolve_git_token, to_credential  # noqa: E402


def prompt_pin(reason: str = "") -> str:
    """PIN z natywnego okna (Windows/tkinter); fallback getpass. Nigdy z ENV/argv."""
    title = "Skarbiec SmartMyOdoo"
    msg = "Podaj PIN" + (f" — {reason}" if reason else "")
    try:
        import tkinter as tk
        from tkinter import simpledialog
    except ImportError:
        return getpass.getpass(f"{msg}: ")
    try:
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        pin = simpledialog.askstring(title, f"{msg}:", show="*", parent=root)
        root.destroy()
    except tk.TclError:
        return getpass.getpass(f"{msg}: ")
    if pin is None:
        raise SystemExit("[skarbiec] Anulowano wpisywanie PIN.")
    return pin


def _unlock(reason: str = ""):
    """Pyta o PIN i zwraca (vk, data). Błędny PIN => czysty komunikat, brak stack-trace."""
    pin = prompt_pin(reason)
    try:
        vk = get_vault_key_from_pin(pin, exit_on_fail=False)
    except ValueError:
        raise SystemExit("[skarbiec] Niewłaściwy PIN — przerywam.")
    return vk, load_vault(vk)


def _token_env(token: str, host: str = "github.com") -> dict:
    """Kopia ENV z wstrzykniętym tokenem. Token NIE w argv (git: przez GIT_CONFIG_*)."""
    env = os.environ.copy()
    env["GH_TOKEN"] = token
    env["GITHUB_TOKEN"] = token
    # credential helper czytający $GH_TOKEN — token nie ląduje w linii poleceń
    helper = '!f() { echo "username=x-access-token"; echo "password=$GH_TOKEN"; }; f'
    n = int(env.get("GIT_CONFIG_COUNT", "0") or "0")
    env[f"GIT_CONFIG_KEY_{n}"] = f"credential.https://{host}.helper"
    env[f"GIT_CONFIG_VALUE_{n}"] = helper
    env["GIT_CONFIG_COUNT"] = str(n + 1)
    return env


def run_with_token(
    cmd: list, host: str = "github.com", workspace_id: str = "default"
) -> int:
    """Odszyfrowuje vault (PIN), wstrzykuje token do podprocesu, uruchamia `cmd`."""
    if not cmd:
        raise SystemExit("[skarbiec] Brak komendy do uruchomienia.")
    vk, data = _unlock(f"dostęp git → {host}")
    cred = resolve_git_token(
        data, host=host, workspace_id=workspace_id, allow_default_fallback=True
    )
    if not cred or not cred.api_key:
        raise SystemExit(
            f"[skarbiec] Brak sekretu git_token dla host={host}, ws={workspace_id}. "
            "Dodaj token (np. 'import-gh') albo popraw host/workspace."
        )
    env = _token_env(cred.api_key, host)
    print(
        f"[skarbiec] token OK (host={host}, login={cred.login or '-'}, "
        f"ws={cred.workspace_id}) — uruchamiam: {cmd[0]} …"
    )
    proc = subprocess.run(cmd, env=env, shell=False)
    return proc.returncode


def import_gh(
    user: str = None,
    host: str = "github.com",
    name: str = None,
    workspace_id: str = "default",
    do_logout: bool = False,
) -> None:
    """Migruje token z keyringu `gh` do Skarbca jako sekret git_token (bez ujawniania wartości)."""
    tok_args = ["gh", "auth", "token", "--hostname", host]
    if user:
        tok_args += ["--user", user]
    res = subprocess.run(tok_args, capture_output=True, text=True)
    token = (res.stdout or "").strip()
    if res.returncode != 0 or not token:
        raise SystemExit(
            f"[skarbiec] Nie pobrano tokenu z gh (rc={res.returncode}): "
            f"{(res.stderr or '').strip()[:200]}"
        )
    login = user or ""
    entry = name or f"GITHUB_PAT_{(user or 'default').upper().replace('-', '_')}"
    record = {
        "type": "git_token",
        "api_key": token,
        "host": host,
        "login": login,
        "workspace_id": workspace_id,
        "scopes": "",
        "resource_owner": "",
        "password": "",
        "url": "",
        "db": "",
        "expires": "",
    }
    # walidacja PRZED zapisem
    if to_credential(entry, record) is None:
        raise SystemExit("[skarbiec] Walidacja git_token nie przeszła — nie zapisuję.")
    vk, data = _unlock(f"zapis tokenu {entry}")
    data[entry] = record
    save_vault(vk, data)
    print(
        f"[skarbiec] Zapisano '{entry}' (git_token, host={host}, "
        f"login={login or '-'}, len={len(token)}). Wartość NIE wypisana."
    )
    if do_logout:
        lo_args = ["gh", "auth", "logout", "--hostname", host]
        if user:
            lo_args += ["--user", user]
        lo = subprocess.run(lo_args, capture_output=True, text=True)
        print(
            f"[skarbiec] gh logout {user or ''}: rc={lo.returncode} "
            f"{(lo.stderr or '').strip()[:160]}"
        )


def main() -> None:
    argv = sys.argv[1:]
    if not argv:
        print(__doc__)
        return
    sub = argv[0]

    if sub == "import-gh":
        p = argparse.ArgumentParser(prog="vault_git import-gh")
        p.add_argument("--user")
        p.add_argument("--host", default="github.com")
        p.add_argument("--name")
        p.add_argument("--ws", default="default")
        p.add_argument("--logout", action="store_true")
        a = p.parse_args(argv[1:])
        import_gh(a.user, a.host, a.name, a.ws, a.logout)
        return

    # tryby uruchomieniowe: run -- <cmd> | git <args> | gh <args> | <cmd...>
    host, workspace_id = "github.com", "default"
    rest = argv
    # opcjonalne globalne --host/--ws przed komendą
    while rest and rest[0] in ("--host", "--ws"):
        flag, val, rest = rest[0], rest[1], rest[2:]
        if flag == "--host":
            host = val
        else:
            workspace_id = val
    if not rest:
        raise SystemExit("[skarbiec] Brak komendy.")
    sub = rest[0]
    if sub == "run":
        cmd = rest[1:]
        if cmd and cmd[0] == "--":
            cmd = cmd[1:]
    elif sub in ("git", "gh"):
        cmd = list(rest)
    else:
        cmd = list(rest)
    sys.exit(run_with_token(cmd, host=host, workspace_id=workspace_id))


if __name__ == "__main__":
    main()
