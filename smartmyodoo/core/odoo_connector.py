import re
import xmlrpc.client  # nosec B411
from typing import List, Dict, Any, Optional


class OdooProjectConnectorError(Exception):
    pass


def sanitize_db_name(name: str) -> str:
    """Czyści nazwę bazy Odoo z etykiety środowiska Odoo.sh.

    Panel Odoo.sh wyświetla bazę jako `slug [branch/version]` (np.
    `myodoo-...-master-6970793 [production/16.0]`), ale do XML-RPC idzie SAM slug.
    Wklejenie pełnej etykiety = `database "... [production/16.0]" does not exist`.
    Obcinamy wszystko od pierwszego ` [` oraz białe znaki (częsta pułapka).
    """
    if not name:
        return name
    return re.split(r"\s*\[", name, maxsplit=1)[0].strip()


class OdooProjectConnector:
    """Connector to Odoo for Project, Task, and Timesheet operations."""

    def __init__(self, credentials: Dict[str, Any]):
        self.url = credentials.get("url", "").rstrip("/")
        # Defensywnie: utnij etykietę Odoo.sh `[branch/version]` z nazwy bazy.
        self.db = sanitize_db_name(credentials.get("db", ""))
        self.username = credentials.get("login", "")
        # Odoo API keys act as passwords
        self.password = credentials.get("api_key") or credentials.get("password", "")

        if not self.url or not self.db or not self.username or not self.password:
            raise OdooProjectConnectorError(
                "Missing required Odoo credentials (url, db, login, password/api_key)."
            )

        self.common = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/common")
        self.uid = self.common.authenticate(self.db, self.username, self.password, {})
        if not self.uid:
            raise OdooProjectConnectorError(
                "Odoo authentication failed. Invalid credentials or database."
            )

        self.models = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/object")

    def execute_kw(
        self,
        model: str,
        method: str,
        args: Optional[List] = None,
        kw: Optional[Dict] = None,
    ):
        """Helper to execute methods on Odoo models via XML-RPC."""
        try:
            return self.models.execute_kw(
                self.db,
                self.uid,
                self.password,
                model,
                method,
                args or [],
                kw or {},
            )
        except Exception as e:
            raise OdooProjectConnectorError(
                f"XML-RPC error on {model}.{method}: {str(e)}"
            )

    def list_tasks(self, project_id: int) -> List[Dict[str, Any]]:
        """Fetch tasks for a specific project."""
        domain = [["project_id", "=", project_id]]
        fields = ["id", "name", "stage_id", "user_ids"]
        return self.execute_kw(
            "project.task", "search_read", [domain], {"fields": fields}
        )

    def get_task(self, task_id: int) -> Optional[Dict[str, Any]]:
        """Fetch a specific task."""
        tasks = self.execute_kw(
            "project.task", "read", [[task_id]], {"fields": ["id", "name"]}
        )
        return tasks[0] if tasks else None

    def create_task(self, project_id: int, name: str) -> int:
        """Create a new task in the project, returns the task ID."""
        vals = {
            "name": name,
            "project_id": project_id,
        }
        return self.execute_kw("project.task", "create", [vals])

    def log_timesheet(
        self, project_id: int, task_id: int, hours: float, description: str
    ) -> int:
        """Create a new timesheet entry."""
        vals = {
            "project_id": project_id,
            "task_id": task_id,
            "name": description,
            "unit_amount": hours,
        }
        # In Odoo 16+, account.analytic.line represents timesheets if project_id is set
        return self.execute_kw("account.analytic.line", "create", [vals])
