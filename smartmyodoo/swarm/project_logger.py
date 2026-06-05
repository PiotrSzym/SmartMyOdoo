import xmlrpc.client
import logging
import os

logger = logging.getLogger(__name__)


class FSMProjectLogger:
    """
    Loguje postęp maszyny stanów FSM jako zadania (project.task)
    lub wiadomości na tablicy (mail.message) do instancji Odoo przez XML-RPC.
    """

    def __init__(
        self,
        url="http://localhost:8069",
        db="LIVE_DB",
        user="admin",
        password="password",
    ):
        self.url = url
        self.db = db
        self.username = user
        self.password = password
        self.uid = None
        self.models = None

        # Odczyt ze zmiennych srodowiskowych jesli istnieja
        self.url = os.getenv("ODOO_URL", self.url)
        self.password = os.getenv("ODOO_PASSWORD", self.password)

    def _connect(self):
        if not self.uid:
            try:
                common = xmlrpc.client.ServerProxy(
                    "{}/xmlrpc/2/common".format(self.url)
                )
                self.uid = common.authenticate(
                    self.db, self.username, self.password, {}
                )
                self.models = xmlrpc.client.ServerProxy(
                    "{}/xmlrpc/2/object".format(self.url)
                )
            except Exception as e:
                logger.warning(f"ProjectLogger: Nie udalo sie polaczyc z Odoo RPC: {e}")
                self.uid = None

    def log_fsm_step(self, task_name: str, status: str, description: str):
        self._connect()
        if not self.uid or not self.models:
            return

        try:
            # Wyszukaj glowny projekt Agenta (jesli nie ma, utworzy)
            project_id = self.models.execute_kw(
                self.db,
                self.uid,
                self.password,
                "project.project",
                "search",
                [[("name", "=", "Agent Swarm Logs")]],
                {"limit": 1},
            )

            if not project_id:
                project_id = [
                    self.models.execute_kw(
                        self.db,
                        self.uid,
                        self.password,
                        "project.project",
                        "create",
                        [{"name": "Agent Swarm Logs"}],
                    )
                ]

            # Zapisz zadanie reprezentujace dzialanie
            self.models.execute_kw(
                self.db,
                self.uid,
                self.password,
                "project.task",
                "create",
                [
                    {
                        "name": f"[{status}] {task_name}",
                        "project_id": project_id[0],
                        "description": description,
                    }
                ],
            )
            logger.info(f"Odoo ProjectLogger: Zapisano log dla {task_name}")

        except Exception as e:
            logger.error(f"Odoo ProjectLogger RPC Error: {e}")
