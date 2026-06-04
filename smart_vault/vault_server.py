import os
import sys
import webbrowser
import threading
import time
import datetime
import logging
from typing import Tuple, Optional
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from functools import wraps

import vault

# Konfiguracja Flaska (statyczne pliki z /ui)
UI_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ui")
if not os.path.exists(UI_DIR):
    os.makedirs(UI_DIR)

app = Flask(__name__, static_folder=UI_DIR, static_url_path="")
CORS(app)

def get_auth_key(pwd: str) -> Tuple[Optional[bytes], Optional[str]]:
    try:
        vk = vault.get_vault_key_from_master(pwd, exit_on_fail=False)
        return vk, "admin"
    except (vault.InvalidToken, ValueError):
        pass
    try:
        vk = vault.get_vault_key_from_pin(pwd, exit_on_fail=False)
        return vk, "user"
    except (vault.InvalidToken, ValueError):
        return None, None

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return jsonify({"error": "Unauthorized"}), 401
        
        pwd = auth_header.split(" ")[1]
        vk, role = get_auth_key(pwd)
        if not vk:
            return jsonify({"error": "Invalid password"}), 401
        
        request.vk = vk
        request.role = role
        request.pwd = pwd
        return f(*args, **kwargs)
    return decorated

@app.route("/")
def index():
    return send_from_directory(UI_DIR, "index.html")

@app.route("/api/status", methods=["GET"])
def status():
    is_init = os.path.exists(vault.VAULT_DATA_FILE)
    return jsonify({"initialized": is_init})

@app.route("/api/init", methods=["POST"])
def init_api():
    if os.path.exists(vault.VAULT_DATA_FILE):
        return jsonify({"error": "Already initialized"}), 400
    data = request.json or {}
    pin = data.get("pin")
    master = data.get("master")
    if not pin or not master:
        return jsonify({"error": "Wymagany PIN i Master Password"}), 400
    if len(pin) < 4:
        return jsonify({"error": "PIN musi mieć min. 4 znaki"}), 400
    try:
        vault.init_vault_core(pin, master)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/auth", methods=["POST"])
def auth():
    data = request.json or {}
    pwd = data.get("password", "")
    vk, role = get_auth_key(pwd)
    if vk:
        return jsonify({"success": True, "role": role})
    return jsonify({"error": "Invalid credentials"}), 401

@app.route("/api/secrets", methods=["GET"])
@require_auth
def get_secrets():
    try:
        data = vault.get_secrets(request.vk)
        return jsonify(data)
    except vault.VaultDecryptionError as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/secrets/<key_name>", methods=["POST"])
@require_auth
def add_or_update_secret(key_name):
    secret_data = request.json or {}
    try:
        data = vault.load_vault(request.vk)
        data[key_name] = {
            "password": secret_data.get("password", ""),
            "login": secret_data.get("login", ""),
            "url": secret_data.get("url", ""),
            "api_key": secret_data.get("api_key", ""),
            "expires": secret_data.get("expires", "")
        }
        vault.save_vault(request.vk, data)
        return jsonify({"success": True})
    except vault.VaultDecryptionError as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/secrets/<key_name>", methods=["DELETE"])
@require_auth
def delete_secret(key_name):
    try:
        data = vault.load_vault(request.vk)
        if key_name in data:
            data[key_name]["deleted_at"] = datetime.datetime.now().isoformat()
            vault.save_vault(request.vk, data)
            return jsonify({"success": True})
        return jsonify({"error": "Not found"}), 404
    except vault.VaultDecryptionError as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/secrets/<key_name>/restore", methods=["POST"])
@require_auth
def restore_secret(key_name):
    try:
        data = vault.load_vault(request.vk)
        if key_name in data and isinstance(data[key_name], dict) and "deleted_at" in data[key_name]:
            del data[key_name]["deleted_at"]
            vault.save_vault(request.vk, data)
            return jsonify({"success": True})
        return jsonify({"error": "Not found or not deleted"}), 404
    except vault.VaultDecryptionError as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/secrets/<key_name>/permanent", methods=["DELETE"])
@require_auth
def permanent_delete_secret(key_name):
    try:
        data = vault.load_vault(request.vk)
        if key_name in data:
            del data[key_name]
            vault.save_vault(request.vk, data)
            return jsonify({"success": True})
        return jsonify({"error": "Not found"}), 404
    except vault.VaultDecryptionError as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/change-pin", methods=["POST"])
@require_auth
def change_pin():
    if request.role != "admin":
        return jsonify({"error": "Admin role required to change PIN"}), 403
    
    new_pin = request.json.get("new_pin")
    if not new_pin:
        return jsonify({"error": "New PIN is required"}), 400
        
    try:
        vault.update_pin(request.vk, new_pin)
        return jsonify({"success": True, "message": "PIN zaktualizowany"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def start_server(port=5050):
    url = f"http://127.0.0.1:{port}"
    print(f"==================================================")
    print(f"|  Serwer Premium Cyber UI działa: {url} |")
    print(f"|  Proszę nie zamykać tej konsoli.               |")
    print(f"==================================================")
    
    # Auto-otwieranie przeglądarki
    def open_browser():
        time.sleep(1)
        webbrowser.open(url)
    threading.Thread(target=open_browser, daemon=True).start()
    
    # Wyłączenie natywnych logów Flaska by nie brudzić konsoli
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    
    app.run(host="127.0.0.1", port=port, debug=False)

if __name__ == "__main__":
    start_server()
