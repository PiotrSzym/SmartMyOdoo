#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""gh_flow.py — bezpieczny helper GitHub flow pod Odoo.sh (nakładka na gh+git).

Koduje NASZ flow (feature -> PR -> staging -> prod) i TWARDE blokady na produkcję,
żeby groźnych akcji nie dało się zrobić przez pomyłkę. Wzorzec bezpieczeństwa:
argv-list (ZERO shell=True), zero interpolacji user-inputu do shella.

Config (opcjonalny scripts/_gh_flow.yml; inaczej domyślne):
  prod_branch: main
  staging_branch: staging
  remote: origin

Komendy:
  status                     bieżący branch + config + stan PR/CI (read-only)
  feature <nazwa>            utwórz feature/<nazwa> od staging i push -u
  pr [--base staging]        PR z bieżącego brancha do bazy (domyślnie staging)
                             (PR z proda: ZABRONIONY; PR do proda: --allow-prod + ostrzeżenie)
  promote                    PR staging -> prod + statusy CI (NIE merge'uje sam)
  push                       bezpieczny push bieżącego brancha (odmawia push na prod)
  install-hook [--dry-run]   git pre-push hook blokujący push na prod (twarda bariera)
"""
import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CFG_FILE = HERE / "_gh_flow.yml"
DEFAULTS = {"prod_branch": "main", "staging_branch": "staging", "remote": "origin"}
NAME_RE = re.compile(r"^[a-z0-9][a-z0-9._/-]{0,60}$", re.I)


def _cfg() -> dict:
    cfg = dict(DEFAULTS)
    if CFG_FILE.exists():
        try:
            import yaml
            data = yaml.safe_load(CFG_FILE.read_text(encoding="utf-8")) or {}
            cfg.update({k: v for k, v in data.items() if k in DEFAULTS and v})
        except Exception:
            pass
    return cfg


def _run(cmd: list[str], capture=True) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=capture, text=True)


def _out(cmd: list[str]) -> str:
    r = _run(cmd)
    return (r.stdout or "").strip()


def _current_branch() -> str:
    b = _out(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    if not b or b == "HEAD":
        sys.exit("❌ Nie jesteś na gałęzi (detached HEAD?) lub to nie repo git.")
    return b


def _require_gh():
    if _run(["gh", "--version"]).returncode != 0:
        sys.exit("❌ Brak GitHub CLI (gh). Zainstaluj i `gh auth login`.")


def cmd_status(args):
    c = _cfg()
    cur = _current_branch()
    print(f"Repo:      {_out(['gh', 'repo', 'view', '--json', 'nameWithOwner', '-q', '.nameWithOwner']) or '?'}")
    print(f"Branch:    {cur}")
    print(f"Config:    prod={c['prod_branch']}  staging={c['staging_branch']}  remote={c['remote']}")
    if cur == c["prod_branch"]:
        print("⚠️  Jesteś na branchu PRODUKCYJNYM — nie pushuj tu bezpośrednio (użyj PR/promote).")
    print("\n--- PR bieżącego brancha ---")
    print(_out(["gh", "pr", "status"]) or "(brak danych PR)")
    checks = _out(["gh", "pr", "checks"])
    if checks:
        print("\n--- Statusy CI (checks) ---")
        print(checks)


def cmd_feature(args):
    c = _cfg()
    name = args.name
    if not NAME_RE.match(name):
        sys.exit("❌ Zła nazwa. Dozwolone: litery/cyfry/._/- (bez spacji), do 60 znaków.")
    branch = name if name.startswith(("feature/", "fix/")) else f"feature/{name}"
    base = c["staging_branch"]
    remote = c["remote"]
    # baza: staging jeśli istnieje zdalnie, inaczej prod
    if _run(["git", "ls-remote", "--exit-code", "--heads", remote, base]).returncode != 0:
        print(f"ℹ️  Brak zdalnego '{base}', odgałęziam od '{c['prod_branch']}'.")
        base = c["prod_branch"]
    _run(["git", "fetch", remote, base], capture=False)
    if _run(["git", "switch", "-c", branch, f"{remote}/{base}"]).returncode != 0:
        sys.exit(f"❌ Nie udało się utworzyć '{branch}' od '{remote}/{base}'.")
    _run(["git", "push", "-u", remote, branch], capture=False)
    print(f"✅ Utworzono i wypchnięto '{branch}' (od {remote}/{base}).")


def _block_prod_source(cur, prod):
    if cur == prod:
        sys.exit(f"⛔ Jesteś na branchu produkcyjnym '{prod}'. "
                 "Zmiany na prod idą wyłącznie przez PR (feature -> staging -> prod).")


def cmd_pr(args):
    _require_gh()
    c = _cfg()
    cur = _current_branch()
    _block_prod_source(cur, c["prod_branch"])
    base = args.base or c["staging_branch"]
    if base == c["prod_branch"] and not args.allow_prod:
        sys.exit(f"⛔ PR prosto do produkcji '{base}' zablokowany. "
                 "Użyj 'promote' (staging->prod) albo dodaj --allow-prod jeśli naprawdę tego chcesz.")
    if base == c["prod_branch"]:
        print("⚠️  UWAGA: PR celuje w PRODUKCJĘ. Merge = build produkcyjny na Odoo.sh.")
    print("ℹ️  Pamiętaj o bumpie wersji w __manifest__.py (bez tego Odoo.sh nie odpali update modułu).")
    cmd = ["gh", "pr", "create", "--base", base, "--head", cur]
    cmd += (["--title", args.title] if args.title else []) + (["--body", args.body] if args.body else [])
    if not args.title:
        cmd.append("--fill")
    _run(cmd, capture=False)


def cmd_promote(args):
    _require_gh()
    c = _cfg()
    prod, staging = c["prod_branch"], c["staging_branch"]
    print(f"Promocja: PR '{staging}' -> '{prod}' (NIE merge'uję automatycznie — merge po review).")
    print("⚠️  Merge do produkcji uruchamia build produkcyjny na Odoo.sh.")
    cmd = ["gh", "pr", "create", "--base", prod, "--head", staging,
           "--title", f"Promote {staging} -> {prod}", "--fill"]
    _run(cmd, capture=False)
    print("\n--- Statusy CI na PR promocyjnym ---")
    print(_out(["gh", "pr", "checks", staging]) or "(brak / PR może dopiero powstał)")
    print("\nMerge dopiero gdy: approvals OK + checks zielone. Zrób to świadomie:")
    print(f"  gh pr merge {staging} --merge   # (albo w UI GitHub)")


def cmd_push(args):
    c = _cfg()
    cur = _current_branch()
    if cur == c["prod_branch"]:
        sys.exit(f"⛔ Bezpośredni push na produkcję '{cur}' zablokowany. "
                 "Prod tylko przez PR (promote). To celowa bariera.")
    _run(["git", "push", "-u", c["remote"], cur], capture=False)
    print(f"✅ Wypchnięto '{cur}' na {c['remote']}.")


PRE_PUSH_HOOK = """#!/bin/sh
# gh_flow.py: TWARDA blokada — zakaz bezposredniego push na branch produkcyjny.
# Prod zmienia sie WYLACZNIE przez PR/merge na GitHub (feature -> staging -> prod).
PROD_REF="refs/heads/%PROD%"
while read local_ref local_sha remote_ref remote_sha; do
  if [ "$remote_ref" = "$PROD_REF" ]; then
    echo "" >&2
    echo "BLOKADA (gh_flow pre-push): push na produkcje '%PROD%' jest zabroniony." >&2
    echo "Prod zmieniaj przez PR/merge na GitHub (scripts/gh_flow.py promote)." >&2
    exit 1
  fi
done
exit 0
"""


def cmd_install_hook(args):
    c = _cfg()
    hook_body = PRE_PUSH_HOOK.replace("%PROD%", c["prod_branch"])
    if args.dry_run:
        print(f"--- pre-push hook (prod='{c['prod_branch']}') — PODGLĄD (dry-run) ---")
        print(hook_body)
        return
    git_dir = _out(["git", "rev-parse", "--git-dir"])
    if not git_dir:
        sys.exit("❌ To nie repo git.")
    hook = Path(git_dir) / "hooks" / "pre-push"
    if hook.exists() and not args.force:
        sys.exit(f"❌ {hook} już istnieje. Użyj --force (zrobię kopię .bak) albo scal ręcznie.")
    if hook.exists():
        backup = hook.with_suffix(".bak")
        backup.write_bytes(hook.read_bytes())
        print(f"ℹ️  Kopia starego hooka: {backup}")
    # LF-only (unikamy pułapki CRLF w shebangu — patrz zepsuty pre-commit w repo)
    hook.write_bytes(hook_body.replace("\r\n", "\n").encode("utf-8"))
    try:
        os.chmod(hook, 0o755)
    except OSError:
        pass
    print(f"✅ Zainstalowano pre-push hook: {hook}\n   Blokuje push na prod '{c['prod_branch']}'.")


def main():
    ap = argparse.ArgumentParser(description="Bezpieczny GitHub flow pod Odoo.sh (gh+git)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status").set_defaults(func=cmd_status)
    f = sub.add_parser("feature"); f.add_argument("name"); f.set_defaults(func=cmd_feature)
    p = sub.add_parser("pr")
    p.add_argument("--base"); p.add_argument("--title"); p.add_argument("--body")
    p.add_argument("--allow-prod", action="store_true")
    p.set_defaults(func=cmd_pr)
    sub.add_parser("promote").set_defaults(func=cmd_promote)
    sub.add_parser("push").set_defaults(func=cmd_push)
    h = sub.add_parser("install-hook")
    h.add_argument("--dry-run", action="store_true"); h.add_argument("--force", action="store_true")
    h.set_defaults(func=cmd_install_hook)
    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
