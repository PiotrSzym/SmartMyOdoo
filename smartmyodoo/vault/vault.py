import os
import sys
import json
import base64
import getpass
import argparse
import datetime
import subprocess
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from typing import Optional, Tuple, List

VAULT_DIR = os.path.dirname(os.path.abspath(__file__))
PIN_SALT_FILE = os.path.join(VAULT_DIR, "pin_salt.cfg")
MASTER_SALT_FILE = os.path.join(VAULT_DIR, "master_salt.cfg")
PIN_KEY_FILE = os.path.join(VAULT_DIR, "pin_key.enc")
MASTER_KEY_FILE = os.path.join(VAULT_DIR, "master_key.enc")
VAULT_DATA_FILE = os.path.join(VAULT_DIR, "vault_data.enc")


class VaultDecryptionError(Exception):
    """Błąd deszyfrowania pliku skarbca."""

    pass


def derive_key(password: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=480000,
    )
    return base64.urlsafe_b64encode(kdf.derive(password.encode("utf-8")))


def get_vault_key_from_pin(pin: str, exit_on_fail: bool = True) -> bytes:
    if not os.path.exists(PIN_SALT_FILE):
        if exit_on_fail:
            print("Vault nie został zainicjalizowany! Użyj 'init'.")
            sys.exit(1)
        raise ValueError("Not initialized")
    with open(PIN_SALT_FILE, "rb") as f:
        salt = f.read()
    f_pin = Fernet(derive_key(pin, salt))
    with open(PIN_KEY_FILE, "rb") as f:
        encrypted_vk = f.read()
    try:
        return f_pin.decrypt(encrypted_vk)
    except (InvalidToken, ValueError):
        if exit_on_fail:
            print("Blad deszyfrowania! Niewlasciwy PIN.")
            sys.exit(1)
        raise ValueError("Invalid PIN")


def get_vault_key_from_master(master_pwd: str, exit_on_fail: bool = True) -> bytes:
    if not os.path.exists(MASTER_SALT_FILE):
        if exit_on_fail:
            print("Vault nie został zainicjalizowany! Użyj 'init'.")
            sys.exit(1)
        raise ValueError("Not initialized")
    with open(MASTER_SALT_FILE, "rb") as f:
        salt = f.read()
    f_master = Fernet(derive_key(master_pwd, salt))
    with open(MASTER_KEY_FILE, "rb") as f:
        encrypted_vk = f.read()
    try:
        return f_master.decrypt(encrypted_vk)
    except (InvalidToken, ValueError):
        if exit_on_fail:
            print("Blad deszyfrowania! Niewlasciwe Master Password.")
            sys.exit(1)
        raise ValueError("Invalid Master Password")


def load_vault(vk: bytes) -> dict:
    if not os.path.exists(VAULT_DATA_FILE):
        raise VaultDecryptionError("Vault data file not found")
    with open(VAULT_DATA_FILE, "rb") as f:
        encrypted_data = f.read()
    try:
        return json.loads(Fernet(vk).decrypt(encrypted_data).decode("utf-8"))
    except (InvalidToken, ValueError, json.JSONDecodeError) as e:
        raise VaultDecryptionError(f"Blad odczytu struktury skarbca: {e}")


def save_vault(vk: bytes, data: dict) -> None:
    with open(VAULT_DATA_FILE, "wb") as f:
        f.write(Fernet(vk).encrypt(json.dumps(data).encode("utf-8")))


def get_secrets(vk: Optional[bytes] = None) -> dict:
    if vk is None:
        pin = getpass.getpass("Podaj PIN dla skarbca: ")
        vk = get_vault_key_from_pin(pin)

    try:
        data = load_vault(vk)
    except VaultDecryptionError:
        print("Blad odczytu struktury skarbca (zly klucz lub plik).")
        sys.exit(1)

    now = datetime.datetime.now()
    keys_to_delete = []
    for k, v in data.items():
        if isinstance(v, dict) and "deleted_at" in v:
            try:
                del_time = datetime.datetime.fromisoformat(v["deleted_at"])
                if (now - del_time).days >= 3:
                    keys_to_delete.append(k)
            except ValueError:
                pass
    if keys_to_delete:
        for k in keys_to_delete:
            del data[k]
        save_vault(vk, data)

    return data


def init_vault_core(pin: str, master: str) -> None:
    if os.path.exists(VAULT_DATA_FILE):
        raise ValueError("Vault juz istnieje!")

    vk = Fernet.generate_key()

    pin_salt = os.urandom(16)
    with open(PIN_SALT_FILE, "wb") as f:
        f.write(pin_salt)
    with open(PIN_KEY_FILE, "wb") as f:
        f.write(Fernet(derive_key(pin, pin_salt)).encrypt(vk))

    master_salt = os.urandom(16)
    with open(MASTER_SALT_FILE, "wb") as f:
        f.write(master_salt)
    with open(MASTER_KEY_FILE, "wb") as f:
        f.write(Fernet(derive_key(master, master_salt)).encrypt(vk))

    save_vault(vk, {})


def update_pin(vk: bytes, new_pin: str) -> None:
    """Zmienia PIN do skarbca. Wymaga poprawnego klucza vk (uzyskanego np. z master password)."""
    pin_salt = os.urandom(16)
    with open(PIN_SALT_FILE, "wb") as f:
        f.write(pin_salt)

    k_pin_new = derive_key(new_pin, pin_salt)
    f_pin_new = Fernet(k_pin_new)

    with open(PIN_KEY_FILE, "wb") as f:
        f.write(f_pin_new.encrypt(vk))


def init_vault() -> None:
    if os.path.exists(VAULT_DATA_FILE):
        print("Vault juz istnieje!")
        sys.exit(1)

    pin = getpass.getpass("Podaj nowy PIN dla skarbca: ")
    confirm_pin = getpass.getpass("Potwierdz PIN: ")
    if pin != confirm_pin:
        print("Blad: PINy sie nie zgadzaja!")
        sys.exit(1)

    master = getpass.getpass("Podaj silne Master Password (do odzyskiwania/GUI): ")
    confirm_master = getpass.getpass("Potwierdz Master Password: ")
    if master != confirm_master:
        print("Blad: Hasla Master sie nie zgadzaja!")
        sys.exit(1)

    init_vault_core(pin, master)
    print("Vault pomyslnie zainicjalizowany.")


def _cli_auth() -> Tuple[bytes, dict]:
    """Pomocnicza funkcja dla CLI: pyta o PIN, autoryzuje i ładuje skarbiec."""
    pin = getpass.getpass("Podaj PIN dla skarbca: ")
    vk = get_vault_key_from_pin(pin)
    try:
        data = load_vault(vk)
        return vk, data
    except VaultDecryptionError:
        print("Blad odczytu struktury skarbca.")
        sys.exit(1)


def add_secret(key_name: str) -> None:
    vk, data = _cli_auth()
    secret_value = getpass.getpass(f"Wklej wartosc (haslo) dla '{key_name}': ")
    data[key_name] = {
        "password": secret_value,
        "login": "",
        "url": "",
        "db": "",
        "api_key": "",
        "expires": "",
    }
    save_vault(vk, data)
    print(f"Klucz '{key_name}' zostal bezpiecznie dodany do skarbca.")


def list_secrets() -> None:
    data = (
        get_secrets()
    )  # get_secrets asks for pin if vk is None and cleans up deleted items
    count = 0
    print("Sekrety w skarbcu:")
    for key, val in data.items():
        if isinstance(val, dict) and "deleted_at" not in val:
            print(f"- {key}")
            count += 1
    if count == 0:
        print("Skarbiec jest pusty.")


def copy_secret(key_name: str) -> None:
    import pyperclip

    _, data = _cli_auth()

    if key_name not in data or (
        isinstance(data[key_name], dict) and "deleted_at" in data[key_name]
    ):
        print(f"Blad: Klucz '{key_name}' nie istnieje w skarbcu.")
        sys.exit(1)

    pyperclip.copy(data[key_name].get("password", ""))
    print(
        f"Wartosc klucza '{key_name}' skopiowana bezpiecznie do schowka! (Wcisnij Ctrl+V)"
    )


def delete_secret(key_name: str) -> None:
    vk, data = _cli_auth()
    if key_name in data:
        data[key_name]["deleted_at"] = datetime.datetime.now().isoformat()
        save_vault(vk, data)
        print(f"Sekret {key_name} przeniesiony do kosza (na 3 dni).")
    else:
        print(f"Sekret {key_name} nie istnieje.")


def restore_secret(key_name: str) -> None:
    vk, data = _cli_auth()
    if (
        key_name in data
        and isinstance(data[key_name], dict)
        and "deleted_at" in data[key_name]
    ):
        del data[key_name]["deleted_at"]
        save_vault(vk, data)
        print(f"Sekret {key_name} przywrocony.")


def run_wrapped_command(cmd_args: List[str]) -> None:
    if not cmd_args:
        print("Blad: Nie podano komendy do uruchomienia.")
        sys.exit(1)

    data = get_secrets()
    env = os.environ.copy()

    for k, obj in data.items():
        if isinstance(obj, dict):
            if "deleted_at" in obj:
                continue
            if obj.get("password"):
                env[f"{k}_PASSWORD"] = str(obj["password"])
            if obj.get("login"):
                env[f"{k}_LOGIN"] = str(obj["login"])
            if obj.get("api_key"):
                env[f"{k}_API_KEY"] = str(obj["api_key"])
            if obj.get("url"):
                env[f"{k}_URL"] = str(obj["url"])
            if obj.get("db"):
                env[f"{k}_DB"] = str(obj["db"])
            env[k] = str(obj.get("password", ""))
        else:
            env[k] = str(obj)

    print("Uruchamiam proces z ukrytymi sekretami...")
    try:
        result = subprocess.run(cmd_args, env=env, shell=False)
        sys.exit(result.returncode)
    except Exception as e:
        print(f"Blad uruchamiania podprocesu: {e}")
        sys.exit(1)


def run_gui() -> None:
    # To zostanie zaimplementowane w vault_server.py
    try:
        from vault_server import start_server

        start_server()
    except ImportError:
        print("Błąd: Moduł serwera GUI nie jest jeszcze zaimplementowany.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="SmartMyVault - Local Zero-Trust Secret Manager"
    )
    subparsers = parser.add_subparsers(dest="command", help="Dostepne komendy")

    subparsers.add_parser(
        "init", help="Inicjalizacja nowego skarbca (PIN + Master Password)"
    )

    add_parser = subparsers.add_parser("add", help="Dodaj nowy sekret")
    add_parser.add_argument("key", help="Nazwa klucza")

    subparsers.add_parser("list", help="Wypisz liste kluczy")

    copy_parser = subparsers.add_parser(
        "copy", help="Skopiuj wartosc sekretu do schowka"
    )
    copy_parser.add_argument("key", help="Nazwa klucza")

    delete_parser = subparsers.add_parser("delete", help="Usun klucz ze skarbca")
    delete_parser.add_argument("key", help="Nazwa klucza")

    restore_parser = subparsers.add_parser("restore", help="Przywroc klucz z kosza")
    restore_parser.add_argument("key", help="Nazwa klucza")

    run_parser = subparsers.add_parser(
        "run", help="Uruchom komende ze wstrzyknietymi zmiennymi ze skarbca"
    )
    run_parser.add_argument(
        "cmd", nargs=argparse.REMAINDER, help="Komenda do uruchomienia"
    )

    subparsers.add_parser("gui", help="Uruchom Premium Cyber UI w przegladarce")

    args = parser.parse_args()

    if args.command == "init":
        init_vault()
    elif args.command == "add":
        add_secret(args.key)
    elif args.command == "list":
        list_secrets()
    elif args.command == "copy":
        copy_secret(args.key)
    elif args.command == "delete":
        delete_secret(args.key)
    elif args.command == "restore":
        restore_secret(args.key)
    elif args.command == "run":
        run_wrapped_command(args.cmd)
    elif args.command == "gui":
        run_gui()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
