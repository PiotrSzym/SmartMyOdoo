import os
import sys

# Ustawienie ścieżki Pythona, żeby łapał moduły lokalne
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from smartmyodoo.vault.vault import get_vault_key_from_pin, get_secrets
from smartmyodoo.mcp.odoo_client import OdooClient

def test_odoo():
    pin = "1111"
    print("Otwieranie Vaulta PIN-em...")
    try:
        vk = get_vault_key_from_pin(pin, exit_on_fail=False)
    except Exception as e:
        print(f"Błąd otwierania Vaulta: {e}")
        return

    print("Pobieranie sekretów...")
    try:
        secrets = get_secrets(vk)

    except Exception as e:
        print(f"Błąd deszyfrowania sekretów: {e}")
        return

    if not secrets:
        print("Vault nie zwrócił żadnych sekretów.")
        return
    
    # Kopiujemy sekrety do środowiska, żeby OdooClient je znalazł
    for k, obj in secrets.items():
        if isinstance(obj, dict):
            if "deleted_at" in obj:
                continue
            if obj.get("password"):
                os.environ[f"{k}_PASSWORD"] = str(obj["password"])
            if obj.get("login"):
                os.environ[f"{k}_LOGIN"] = str(obj["login"])
            if obj.get("url"):
                os.environ[f"{k}_URL"] = str(obj["url"])
            if obj.get("db"):
                os.environ[f"{k}_DB"] = str(obj["db"])
            os.environ[k] = str(obj.get("password", ""))
        else:
            os.environ[k] = str(obj)
        print(f"  Zaladowano sekret: {k}")

    print("\nDostępne zmienne ODOO w środowisku po załadowaniu z Vaulta:")
    for k, v in os.environ.items():
        if "ODOO" in k:
            print(f"{k} = {'***' if 'PASSWORD' in k or 'KEY' in k else v}")

    print("\nSzukam konfiguracji dla jakiegokolwiek Odoo...")
    url, db, username, password = None, None, None, None
    for k in os.environ.keys():
        if k.endswith("_URL") and "ODOO" in k:
            base = k.replace("_URL", "")
            url = os.environ.get(f"{base}_URL")
            db = os.environ.get(f"{base}_DB")
            if not db and url:
                # Odoo SaaS fallback:
                import urllib.parse
                parsed = urllib.parse.urlparse(url)
                if parsed.netloc:
                    db = parsed.netloc.split(".")[0]
            
            username = os.environ.get(f"{base}_USERNAME") or os.environ.get(f"{base}_LOGIN")
            password = os.environ.get(f"{base}_PASSWORD")
            print(f"Znaleziono bazę: {base} ({url}, User: {username})")
            if url and url.startswith("http") and username and password:
                break
    
    if not (url and username and password):
        print("Nie znaleziono kompletnych danych logowania Odoo w Vaulcie!")
        return

    import xmlrpc.client
    # Próbujemy wylistować bazy jeśli się da
    try:
        db_proxy = xmlrpc.client.ServerProxy(f"{url.rstrip('/')}/xmlrpc/db")
        db_list = db_proxy.list()
        print(f"\nDostępne bazy na serwerze: {db_list}")
        if db_list:
            db_candidates = db_list
    except Exception as e:
        print(f"\nNie udało się pobrać listy baz: {e}")
        db_candidates = []

    if not db_candidates:
        import urllib.parse
        parsed = urllib.parse.urlparse(url)
        host = parsed.netloc
        db_candidates = [
            host,                     # np. ps-myodoo-test-knowlage-piotr.odoo.com
            host.split(".")[0],       # np. ps-myodoo-test-knowlage-piotr
            host.replace("-", "_"),
            host.split(".")[0].replace("-", "_")
        ]

    print("\nInicjalizacja OdooClient... Próbuję dopasować nazwę bazy:")
    
    client = None
    candidate = "ps-myodoo-test-knowlage-piotr"
    print(f"  -> Próbuję bazę: {candidate} z nowym hasłem")
    os.environ["ODOO_URL"] = url
    os.environ["ODOO_DB"] = candidate
    os.environ["ODOO_USERNAME"] = username
    os.environ["ODOO_PASSWORD"] = "1234"
    
    import xmlrpc.client
    common = xmlrpc.client.ServerProxy("{}/xmlrpc/2/common".format(url))
    print("Odoo Server Version:", common.version())

    for db_cand in [
        "ps-myodoo-test-knowlage-piotr-main-32905703"
    ]:
        print(f"\n  -> Próbuję bazę: {db_cand} z nowym hasłem")
        os.environ["ODOO_DB"] = db_cand
        c = OdooClient(workspace_id="default")
        try:
            c.connect()
            print(f"  [!] SUKCES! Zalogowano do bazy: {db_cand}")
            client = c
            
            # Pobieranie kontaktów
            partners = c.search_read("res.partner", [], ["name"], limit=1000)
            print(f"\n✅ ZNALAZŁEM KONTAKTY W BAZIE! Liczba kontaktów: {len(partners)}")
            
            break
        except Exception as e:
            print(f"  Błąd: {e}")
    
    if not client:
        print("\nNie udało się zalogować przy użyciu żadnej z przewidywanych nazw baz :(")
        return
    
    try:
        print("Nawiązywanie połączenia z Odoo...")
        client.connect()
        print("Zalogowano pomyślnie!")
    except Exception as e:
        print(f"Błąd logowania do Odoo: {e}")
        return

    print("\nPobieranie kontaktów (res.partner)...")
    try:
        records = client.search_read("res.partner", [], ["name", "email", "phone"], limit=5)
        count = len(records)
        print(f"\nUdało się! Pobrane rekordy (znaleziono {count}):")
        for idx, rec in enumerate(records):
            print(f"{idx+1}. {rec.get('name')} (Email: {rec.get('email')}, Tel: {rec.get('phone')})")
        
        # Jeśli api pozwala policzyć total (niestety OdooClient xmlrpc domyślnie search_read tylko zwraca listę)
        # można wywołać 'search_count' ale nasza klasa go nie wspiera. Wystarczy liczba pobranych na probe.
    except Exception as e:
        print(f"Błąd podczas odczytu danych: {e}")

if __name__ == "__main__":
    test_odoo()
