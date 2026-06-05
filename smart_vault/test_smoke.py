import pytest
import os
import requests
import multiprocessing
import time
import vault
import vault_server

# Simple smoke test for the Flask server running locally
def run_server():
    vault_server.app.run(port=5055, use_reloader=False)

@pytest.fixture(scope="module")
def server_process():
    # Setup fresh vault data
    vault.PIN_SALT_FILE = "smoke_pin_salt.cfg"
    vault.MASTER_SALT_FILE = "smoke_master_salt.cfg"
    vault.PIN_KEY_FILE = "smoke_pin_key.enc"
    vault.MASTER_KEY_FILE = "smoke_master_key.enc"
    vault.VAULT_DATA_FILE = "smoke_vault_data.enc"
    
    files = [
        vault.PIN_SALT_FILE, vault.MASTER_SALT_FILE, 
        vault.PIN_KEY_FILE, vault.MASTER_KEY_FILE, vault.VAULT_DATA_FILE
    ]
    for f in files:
        if os.path.exists(f): os.remove(f)
        
    p = multiprocessing.Process(target=run_server)
    p.start()
    time.sleep(1) # wait for server to start
    yield
    p.terminate()
    p.join()
    
    for f in files:
        if os.path.exists(f): os.remove(f)

def test_smoke_endpoints(server_process):
    base_url = "http://127.0.0.1:5055/api"
    
    # Test status
    res = requests.get(f"{base_url}/status")
    assert res.status_code == 200
    assert res.json()["initialized"] is False
    
    # Test init
    res = requests.post(f"{base_url}/init", json={"pin": "smoke", "master": "smoke_master"})
    assert res.status_code == 200
    
    # Test Auth
    res = requests.post(f"{base_url}/auth", json={"password": "smoke"})
    assert res.status_code == 200
    assert res.json()["role"] == "user"
    
    # Test Auth Admin
    res = requests.post(f"{base_url}/auth", json={"password": "smoke_master"})
    assert res.status_code == 200
    assert res.json()["role"] == "admin"
    
    # Add secret
    headers = {"Authorization": "Bearer smoke"}
    res = requests.post(f"{base_url}/secrets/SMOKE_KEY", json={"password": "test"}, headers=headers)
    assert res.status_code == 200
    
    # Read secrets
    res = requests.get(f"{base_url}/secrets", headers=headers)
    assert res.status_code == 200
    assert "SMOKE_KEY" in res.json()
