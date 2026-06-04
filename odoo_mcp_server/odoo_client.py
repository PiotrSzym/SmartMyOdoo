import xmlrpc.client
import os

class OdooClient:
    """Klient API dla Odoo korzystający z XML-RPC. Inicjalizuje się zmiennymi ze środowiska (SmartMyVault)."""
    
    def __init__(self):
        self.url = os.getenv("ODOO_URL")
        self.db = os.getenv("ODOO_DB")
        self.username = os.getenv("ODOO_USERNAME")
        self.password = os.getenv("ODOO_PASSWORD")
        self.uid = None
        self.models = None
        
    def connect(self):
        """Uwierzytelnia się w Odoo i zwraca True w przypadku sukcesu."""
        if not all([self.url, self.db, self.username, self.password]):
            raise ValueError("Brak konfiguracji Odoo w zmiennych środowiskowych.")
            
        common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(self.url))
        self.uid = common.authenticate(self.db, self.username, self.password, {})
        
        if not self.uid:
            raise PermissionError("Błąd autoryzacji do Odoo. Sprawdź poświadczenia w SmartMyVault.")
            
        self.models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(self.url))
        return True

    def search_read(self, model: str, domain: list, fields: list = None, limit: int = 10):
        """Wyszukuje i czyta rekordy z podanego modelu."""
        if not self.uid:
            self.connect()
            
        kwargs = {}
        if fields:
            kwargs['fields'] = fields
        if limit:
            kwargs['limit'] = limit
            
        records = self.models.execute_kw(
            self.db, self.uid, self.password,
            model, 'search_read', [domain], kwargs
        )
        return records
        
    def get_model_fields(self, model: str):
        """Pobiera strukturę (schemat) danego modelu."""
        if not self.uid:
            self.connect()
            
        fields_info = self.models.execute_kw(
            self.db, self.uid, self.password,
            model, 'fields_get', [], {'attributes': ['string', 'help', 'type']}
        )
        return fields_info

# Globalna instancja klienta
odoo = OdooClient()
