from mcp.server.fastmcp import FastMCP
import os
import sys

# Dodanie obecnego folderu do sys.path by móc importować lokalne pliki
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from token_governor import governor
from odoo_client import odoo
import shadow_mode
import database_magic

# Inicjalizacja serwera MCP dla Odoo
mcp = FastMCP("SmartMyOdoo-MCP")

# Zmienne środowiskowe Odoo 
# (UWAGA: Agent nie używa `vault.py` bezpośrednio. Uruchamiamy serwer poprzez: `python vault.py run python odoo_mcp_server/server.py`)
ODOO_URL = os.getenv("ODOO_URL")
ODOO_DB = os.getenv("ODOO_DB")
ODOO_USER = os.getenv("ODOO_USERNAME")
ODOO_PASS = os.getenv("ODOO_PASSWORD")

@mcp.tool()
def check_status() -> str:
    """Sprawdź czy serwer MCP dla Odoo jest włączony i ma dostęp do konfiguracji z Vaulta."""
    status = "✅ Odoo MCP Server is running.\n\n"
    
    if ODOO_URL and ODOO_DB and ODOO_USER:
        status += f"🔒 SmartMyVault Integration: Aktywna. Wstrzyknięto poświadczenia dla bazy: {ODOO_DB} pod adresem {ODOO_URL}.\n"
    else:
        status += "⚠️ OSTRZEŻENIE: Brak konfiguracji Odoo w zmiennych środowiskowych! Serwer musi zostać uruchomiony przez komendę 'vault run'.\n"
        
    budget = governor.get_status()
    status += f"💰 Budżet sesji (Token Governor): wydano ${budget['spent_usd']} z dozwolonych ${budget['max_budget_usd']}\n"
    
    return status

@mcp.tool()
def read_odoo_schema(model_name: str) -> dict:
    """Pobierz definicje i typy kolumn w konkretnej tabeli Odoo (modelu), np. 'res.partner' lub 'account.move'."""
    try:
        return odoo.get_model_fields(model_name)
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def search_odoo_records(model_name: str, domain: str = "[]", fields: str = "[]", limit: int = 10) -> dict:
    """
    Wyszukaj rekordy w Odoo. 
    Domain to stringifikowana lista list, np. "[['is_company', '=', True]]".
    Fields to stringifikowana lista kolumn, np. "['name', 'email']". Jeśli pusta, zwraca wszystkie.
    """
    import json
    try:
        domain_list = json.loads(domain) if domain else []
        fields_list = json.loads(fields) if fields else []
        records = odoo.search_read(model_name, domain_list, fields_list, limit)
        return {"records": records, "count": len(records)}
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def propose_odoo_update(model_name: str, record_id: int, values_json: str, reason: str) -> str:
    """
    Zaproponuj zmianę w Odoo (Shadow Mode). Agent nie ma praw do bezpośredniego zapisu (WRITE).
    Musisz wywołać to narzędzie podając JSON ze zmianami. Użytkownik otrzyma to do akceptacji.
    values_json musi być poprawnym stringiem JSON (np. '{"name": "Nowa Nazwa"}').
    """
    import json
    try:
        values = json.loads(values_json)
        proposal = shadow_mode.create_proposal("update", model_name, [record_id], values, reason)
        return f"✅ Propozycja zmiany zapisana pomyślnie. Czekamy na akceptację przez człowieka.\nID Propozycji: {proposal['id']}"
    except Exception as e:
        return f"❌ Błąd zapisu propozycji: {str(e)}"

@mcp.tool()
def propose_magic_fix(fix_type: str, record_id: int, reason: str) -> str:
    """
    Zastosuj "Magię Bazodanową". Pozwala agentowi zażądać wykonania skryptu naprawczego,
    który omija normalne blokady Odoo (np. usunięcie zatwierdzonej faktury, zmiana jednostki miary produktu z historią).
    fix_type musi być jednym z: 'force_cancel_invoice', 'unlock_stock_move', 'change_uom_on_product'.
    """
    try:
        proposal = database_magic.propose_magic_fix(fix_type, record_id, reason)
        return f"🪄 Propozycja Magii Bazodanowej przygotowana. Oczekuje na weryfikację pracownika. ID Propozycji: {proposal['id']}"
    except Exception as e:
        return f"❌ Błąd zapisu propozycji magicznej: {str(e)}"

if __name__ == "__main__":
    # Uruchomienie serwera na standardowym wejściu/wyjściu (stdio) dla integracji z agentem
    mcp.run(transport='stdio')
