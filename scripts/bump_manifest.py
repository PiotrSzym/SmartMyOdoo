#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""bump_manifest.py — bezpieczny bump wersji modułu Odoo w __manifest__.py.

Schemat domu (baza wiedzy art. 93): <wersja_odoo>.X.Y.Z (np. 16.0.1.2.3)
  X major = zmiana niekompatybilna (zeruje Y,Z)
  Y minor = feature/zmiana        (zeruje Z)
  Z patch = fix wsteczny
Prefiks wersji Odoo (np. 16.0) zachowany. Parsowanie regexem — NIGDY eval().

Po co: na Odoo.sh bez bumpu wersji moduł NIE zostanie zaktualizowany (-u się nie odpali).

Użycie:
  python scripts/bump_manifest.py <modul|sciezka/__manifest__.py> {major|minor|patch} [--dry-run]
Przyklady:
  python scripts/bump_manifest.py custom_addons/smart_chat patch
  python scripts/bump_manifest.py path/to/__manifest__.py minor --dry-run
"""
import argparse
import re
import sys
from pathlib import Path

VER_RE = re.compile(r"""(['"])version\1\s*:\s*(['"])(?P<ver>[^'"]+)\2""")


def _find_manifest(target: str) -> Path:
    p = Path(target)
    if p.is_dir():
        p = p / "__manifest__.py"
    if not p.exists():
        sys.exit(f"❌ Nie znaleziono manifestu: {p}")
    return p


def _split_version(ver: str):
    """Zwraca (prefix_list, [X,Y,Z], suffix_str). Ostatnie 3 liczby = moduł X.Y.Z."""
    m = re.match(r"^(?P<num>\d+(?:\.\d+)*)(?P<suf>.*)$", ver.strip())
    if not m or not m.group("num"):
        sys.exit(f"❌ Nie rozumiem wersji '{ver}' (brak części numerycznej).")
    parts = [int(x) for x in m.group("num").split(".")]
    suffix = m.group("suf")
    if len(parts) >= 3:
        prefix, mod = parts[:-3], parts[-3:]
    elif len(parts) == 2:
        prefix, mod = [], [parts[0], parts[1], 0]
    else:  # len == 1
        prefix, mod = [], [parts[0], 0, 0]
    return prefix, mod, suffix


def _bump(mod, level):
    x, y, z = mod
    if level == "patch":
        z += 1
    elif level == "minor":
        y += 1; z = 0
    elif level == "major":
        x += 1; y = 0; z = 0
    return [x, y, z]


def main():
    ap = argparse.ArgumentParser(description="Bump wersji modułu Odoo (__manifest__.py)")
    ap.add_argument("target", help="katalog modułu albo ścieżka do __manifest__.py")
    ap.add_argument("level", choices=["major", "minor", "patch"])
    ap.add_argument("--dry-run", action="store_true", help="pokaż zmianę bez zapisu")
    args = ap.parse_args()

    manifest = _find_manifest(args.target)
    text = manifest.read_text(encoding="utf-8")
    m = VER_RE.search(text)
    if not m:
        sys.exit(f"❌ Brak klucza 'version' w {manifest}.")
    old_ver = m.group("ver")
    prefix, mod, suffix = _split_version(old_ver)
    new_mod = _bump(mod, args.level)
    new_ver = ".".join(str(n) for n in (prefix + new_mod))

    print(f"Moduł:   {manifest}")
    print(f"Wersja:  {old_ver}  --({args.level})-->  {new_ver}")
    if suffix:
        print(f"ℹ️  Sufiks '{suffix}' pominięty w nowej wersji (bump = wydanie).")

    if args.dry_run:
        print("(dry-run — nic nie zapisano)")
        return

    # Podmiana TYLKO wartości version (zachowujemy oryginalne cudzysłowy).
    q = m.group(2)
    new_text = text[:m.start()] + f"{m.group(1)}version{m.group(1)}: {q}{new_ver}{q}" + text[m.end():]
    manifest.write_text(new_text, encoding="utf-8")
    print(f"✅ Zapisano wersję {new_ver} w {manifest}.")
    print("   Pamiętaj: commit + push → Odoo.sh odpali update modułu. Rozważ skrypt migracyjny "
          f"(migrations/{new_ver}/) jeśli zmieniasz schema.")


if __name__ == "__main__":
    main()
