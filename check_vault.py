from smartmyodoo.vault import vault

vk = vault.get_vault_key_from_pin("1111", exit_on_fail=False)
data = vault.load_vault(vk)
print("Klucze w sejfie:", list(data.keys()))
for k, v in data.items():
    if isinstance(v, dict) and "deleted_at" not in v:
        print(f"  [{k}]")
        print(f"    url: {v.get('url', '')}")
        print(f"    db: {v.get('db', '')}")
        print(f"    login: {v.get('login', '')}")
        print(f"    password set: {bool(v.get('password'))}")
        print(f"    api_key set: {bool(v.get('api_key'))}")
