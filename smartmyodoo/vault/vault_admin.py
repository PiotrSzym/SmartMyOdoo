# -*- coding: utf-8 -*-
"""Zmiana PIN / hasla Master przez NATYWNE OKNA (tkinter).

Powod: w tym srodowisku getpass w terminalu nie dostaje interaktywnego wejscia
i zawiesza sie. Ten helper pyta o wartosci w oknach dialogowych (jak vault_git),
autoryzuje OBECNYM PIN-em (lub Masterem) i przepakowuje ten sam klucz vk.

Uzycie (uruchamiane w tle, okna wyskakuja na pulpicie):
    python -m smartmyodoo.vault.vault_admin changepin
    python -m smartmyodoo.vault.vault_admin changemaster
"""
import os
import sys

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from smartmyodoo.vault.vault import (  # noqa: E402
    get_vault_key_from_pin,
    get_vault_key_from_master,
    update_pin,
    update_master,
)


def _ask(title: str, prompt: str) -> str:
    """Okno z ukrytym wpisem (haslo/PIN). Zwraca tekst lub konczy przy Anuluj."""
    import tkinter as tk
    from tkinter import simpledialog

    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    val = simpledialog.askstring(title, prompt, show="*", parent=root)
    root.destroy()
    if val is None:
        raise SystemExit("[skarbiec] Anulowano.")
    return val


def _info(title: str, msg: str) -> None:
    import tkinter as tk
    from tkinter import messagebox

    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    messagebox.showinfo(title, msg, parent=root)
    root.destroy()


def _unlock():
    """Autoryzacja OBECNYM PIN-em; pusty PIN => pyta o obecne haslo Master."""
    pin = _ask("Skarbiec — autoryzacja", "Podaj OBECNY PIN (Enter puste = uzyj Master):")
    try:
        if pin.strip() == "":
            master = _ask("Skarbiec — autoryzacja", "Podaj OBECNE haslo Master:")
            return get_vault_key_from_master(master, exit_on_fail=False)
        return get_vault_key_from_pin(pin, exit_on_fail=False)
    except ValueError:
        _info("Skarbiec", "Niewlasciwe poswiadczenie — przerywam.")
        raise SystemExit("[skarbiec] Niewlasciwe poswiadczenie.")


def change_pin() -> None:
    vk = _unlock()
    n1 = _ask("Zmiana PIN", "NOWY PIN (min 4 znaki):")
    n2 = _ask("Zmiana PIN", "Potwierdz NOWY PIN:")
    if n1 != n2:
        _info("Zmiana PIN", "PINy sie nie zgadzaja — nic nie zmieniono.")
        raise SystemExit("[skarbiec] PINy sie nie zgadzaja.")
    if len(n1) < 4:
        _info("Zmiana PIN", "PIN za krotki (min 4) — nic nie zmieniono.")
        raise SystemExit("[skarbiec] PIN za krotki.")
    update_pin(vk, n1)
    _info("Zmiana PIN", "PIN zaktualizowany.")
    print("[skarbiec] PIN zaktualizowany.")


def change_master() -> None:
    vk = _unlock()
    n1 = _ask("Zmiana hasla Master", "NOWE haslo Master (min 8 znakow):")
    n2 = _ask("Zmiana hasla Master", "Potwierdz NOWE haslo Master:")
    if n1 != n2:
        _info("Zmiana Master", "Hasla sie nie zgadzaja — nic nie zmieniono.")
        raise SystemExit("[skarbiec] Hasla sie nie zgadzaja.")
    if len(n1) < 8:
        _info("Zmiana Master", "Haslo za krotkie (min 8) — nic nie zmieniono.")
        raise SystemExit("[skarbiec] Master za krotki (min 8).")
    update_master(vk, n1)
    _info("Zmiana Master", "Haslo Master zaktualizowane.")
    print("[skarbiec] Haslo Master zaktualizowane.")


def export_backup(out_path: str) -> None:
    """Zaszyfrowany backup Skarbca do out_path (klucz z PIN + losowa sol w blobie)."""
    from smartmyodoo.vault.vault import export_vault, VaultDecryptionError

    pin = _ask(
        "Skarbiec — backup", "Podaj PIN (do zaszyfrowania kopii zapasowej):"
    )
    try:
        export_vault(out_path, pin=pin)
    except VaultDecryptionError as e:
        _info("Backup Skarbca", f"Nieudany: {e}")
        raise SystemExit(f"[skarbiec] Export nieudany: {e}")
    _info(
        "Backup Skarbca",
        "Zapisano zaszyfrowana kopie:\n"
        f"{out_path}\n\n"
        "UWAGA: do odtworzenia potrzebny bedzie TEN sam (nowy) PIN.\n"
        "Trzymaj plik poza repo, najlepiej na innym nosniku.",
    )
    print(f"[skarbiec] Export OK: {out_path}")


def main() -> None:
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "changepin":
        change_pin()
    elif cmd == "changemaster":
        change_master()
    elif cmd == "export":
        out = sys.argv[2] if len(sys.argv) > 2 else r"C:\od_zera_do_ai\vault-backup.enc"
        export_backup(out)
    else:
        print(
            "uzycie: python -m smartmyodoo.vault.vault_admin changepin|changemaster|export [sciezka]"
        )


if __name__ == "__main__":
    main()
