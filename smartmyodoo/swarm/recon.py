from smartmyodoo.swarm.models import EnvironmentInfo

class EnvironmentRecon:
    """Klasa odpowiedzialna za automatyczne rozpoznawanie środowiska Odoo (wersja, hosting, edycja)."""

    def __init__(self, client):
        self.client = client

    def classify_hosting(self, url: str) -> str:
        """Klasyfikuje typ hostingu na podstawie adresu URL instancji Odoo."""
        if not url:
            return "unknown"
        if "odoo.com" in url:
            return "saas"
        elif "odoo.sh" in url:
            return "odoo_sh"
        else:
            return "on_premise"

    def detect_edition(self) -> str:
        """Rozpoznaje edycję (Community/Enterprise) weryfikując licencję modułu 'base_setup'."""
        try:
            records = self.client.search_read(
                "ir.module.module", 
                [("name", "=", "base_setup")], 
                ["license"]
            )
            if records and records[0].get("license") == "OEEL-1":
                return "enterprise"
            return "community"
        except Exception:
            return "community"

    def detect_version(self) -> EnvironmentInfo:
        """Pobiera pełne informacje o środowisku poprzez API XML-RPC (wersja, edycja, hosting)."""
        try:
            version_info = self.client.version()
            odoo_version = version_info.get("server_version", "unknown")
            hosting = self.classify_hosting(getattr(self.client, "url", ""))
            edition = self.detect_edition()
            return EnvironmentInfo(
                odoo_version=odoo_version,
                edition=edition,
                hosting_type=hosting
            )
        except Exception:
            # Graceful fail
            return EnvironmentInfo(
                odoo_version="unknown",
                edition="unknown",
                hosting_type="unknown"
            )

