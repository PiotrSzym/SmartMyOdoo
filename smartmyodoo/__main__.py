import os
import sys
import time

from smartmyodoo.cli import InteractiveCLI
from smartmyodoo.swarm.executor import SkillExecutor
from smartmyodoo.swarm.llm_client import OpenRouterClient
from smartmyodoo.swarm.skills.skill_config import SkillConfig
from smartmyodoo.swarm.models import SkillName
from smartmyodoo.swarm.sandbox import SandboxManager


def main():
    # ── Database setup ──
    from smartmyodoo.core.database import engine, SessionLocal
    from smartmyodoo.core import models as db_models
    db_models.Base.metadata.create_all(bind=engine)
    db_session = SessionLocal()

    # ── Chat Repository (EP-1: Historia chatów) ──
    from smartmyodoo.core.chat_repository import ChatRepository
    chat_repo = ChatRepository(db=db_session)

    workspace_id = os.environ.get("SMARTMYODOO_WORKSPACE", "default")
    session_id = f"cli-{int(time.time())}"

    # ── Sandbox Manager (EP-2: Rollback) ──
    sandbox = SandboxManager()

    # ── LLM Client ──
    api_key = os.environ.get("OPENROUTER_API_KEY", "dummy_key_for_testing")
    llm_client = OpenRouterClient(
        api_key=api_key,
        model="openrouter/meta-llama/llama-3.1-8b-instruct",
    )

    # ── Executor z pełną integracją ──
    executor = SkillExecutor(
        llm_client=llm_client,
        chat_repo=chat_repo,
        workspace_id=workspace_id,
        session_id=session_id,
        sandbox=sandbox,
    )

    # ── Skill Config ──
    try:
        config = SkillConfig(
            name=SkillName.ODOO_DEVELOPER,
            system_prompt=(
                "Jesteś ekspertem Odoo Developer. "
                "Masz do dyspozycji narzędzia do interakcji z Odoo. "
                "Odpowiadaj krótko i konkretnie."
            ),
            allowed_tools=[
                "odoo_search", "odoo_schema", "odoo_create",
                "search_knowledge_base", "scaffold_module",
                "read_odoo_log", "search_odoo_code",
            ],
            red_flags=[],
            recommended_model="openrouter/meta-llama/llama-3.1-8b-instruct",
        )
    except Exception as e:
        print(f"Błąd konfiguracji Skilla: {str(e)}")
        sys.exit(1)

    def callback(message: str) -> dict:
        # Aktualizuj session_id w executor (może się zmienić po /sessions)
        executor.session_id = cli.session_id
        return executor.execute(config, message)

    # ── CLI z historią sesji ──
    cli = InteractiveCLI(
        callback=callback,
        chat_repo=chat_repo,
        workspace_id=workspace_id,
        session_id=session_id,
    )
    try:
        cli.run()
    finally:
        db_session.close()


if __name__ == "__main__":
    main()

