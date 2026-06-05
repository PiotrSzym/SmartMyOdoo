import httpx
import logging

logger = logging.getLogger(__name__)


class OdooDBManager:
    """
    Manager bazy danych Odoo wykorzystujący natywne API (/web/database/...).
    Służy do tworzenia 'Scratchpad DB' (klonowania) i przywracania stanu przed ACTUATION.
    """

    def __init__(self, odoo_url: str, master_password: str):
        self.odoo_url = odoo_url.rstrip("/")
        self.master_password = master_password
        self.client = httpx.Client(timeout=120.0)

    def duplicate_database(self, original_db: str, new_db: str) -> bool:
        """
        Klonuje oryginalną bazę danych do nowej (Scratchpad DB).
        """
        url = f"{self.odoo_url}/web/database/duplicate"
        data = {
            "master_pwd": self.master_password,
            "name": original_db,
            "new_name": new_db,
        }
        try:
            response = self.client.post(url, data=data)
            # Odoo API w przypadku sukcesu robi redirect (303) lub po prostu 200 z poprawną strukturą
            if response.status_code in [200, 303]:
                logger.info(
                    f"Pomyślnie utworzono Scratchpad DB: {new_db} z {original_db}"
                )
                return True
            logger.error(
                f"Błąd klonowania bazy: {response.status_code} - {response.text}"
            )
            return False
        except Exception as e:
            logger.error(f"Wyjątek podczas klonowania bazy: {str(e)}")
            return False

    def drop_database(self, db_name: str) -> bool:
        """
        Usuwa bazę danych (używane podczas rollbacku lub teardownu).
        """
        url = f"{self.odoo_url}/web/database/drop"
        data = {"master_pwd": self.master_password, "name": db_name}
        try:
            response = self.client.post(url, data=data)
            if response.status_code in [200, 303]:
                logger.info(f"Usunięto bazę danych: {db_name}")
                return True
            logger.error(
                f"Błąd usuwania bazy: {response.status_code} - {response.text}"
            )
            return False
        except Exception as e:
            logger.error(f"Wyjątek podczas usuwania bazy: {str(e)}")
            return False
