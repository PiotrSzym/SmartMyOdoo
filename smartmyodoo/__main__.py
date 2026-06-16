import argparse
import sys
import time

from smartmyodoo.cli import InteractiveCLI
from smartmyodoo.http_client import SmartMyOdooClient


def _run_seed(args) -> None:
    """Buduje lokalny indeks wiedzy ze źródeł (ADR-015).

    --shared <dir>   → warstwa współdzielona (__shared__)
    --private <dir>  → warstwa prywatna (wymaga --workspace <id>)
    Domyślnie (bez flag): seeduje `knowledge/` jako shared.
    """
    from smartmyodoo.swarm.brain.seed_knowledge import seed_knowledge_base

    private = getattr(args, "private", None)
    seed_workspace = getattr(args, "seed_workspace", None)

    if private:
        if not seed_workspace:
            print("❌ --private wymaga --workspace <id> (warstwa prywatna).")
            sys.exit(1)
        seed_knowledge_base(private, workspace_id=seed_workspace)

    shared = getattr(args, "shared", None)
    if shared:
        seed_knowledge_base(shared, workspace_id=None)

    if not shared and not private:
        # Domyślnie: współdzielona wiedza z wersjonowanego folderu knowledge/.
        seed_knowledge_base("knowledge", workspace_id=None)


def main():
    parser = argparse.ArgumentParser(description="SmartMyOdoo CLI and Worker")
    subparsers = parser.add_subparsers(dest="command")

    # Worker subcommand
    subparsers.add_parser("worker", help="Start background worker daemon")

    # Seed subcommand (ADR-015): odbudowa lokalnego indeksu wiedzy ze źródeł.
    seed_parser = subparsers.add_parser(
        "seed", help="Zbuduj lokalny indeks wiedzy z wersjonowanych źródeł"
    )
    seed_parser.add_argument(
        "--shared",
        type=str,
        default=None,
        help="Katalog ze współdzieloną wiedzą (warstwa __shared__), np. knowledge/",
    )
    seed_parser.add_argument(
        "--private",
        type=str,
        default=None,
        help="Katalog z wiedzą prywatną (wymaga --workspace)",
    )
    seed_parser.add_argument(
        "--workspace",
        dest="seed_workspace",
        type=str,
        default=None,
        help="ID workspace dla warstwy prywatnej (--private)",
    )

    # CLI arguments (backward compatibility without 'cli' subcommand)
    parser.add_argument(
        "--url",
        type=str,
        default="http://127.0.0.1:8000",
        help="URL of the FastAPI server",
    )
    parser.add_argument("--workspace", type=str, default="default", help="Workspace ID")

    args = parser.parse_args()

    if args.command == "worker":
        import asyncio
        import os
        import signal
        from smartmyodoo.workers.main_worker import main as worker_main, handle_signal

        if os.name == "nt":
            signal.signal(signal.SIGINT, handle_signal)
            signal.signal(signal.SIGTERM, handle_signal)
        asyncio.run(worker_main())
        return

    if args.command == "seed":
        _run_seed(args)
        return

    client = SmartMyOdooClient(base_url=args.url)

    print("==================================================")
    print(f"|  SmartMyOdoo CLI connecting to: {args.url}")
    print("==================================================")

    # Login
    try:
        import getpass

        pin = getpass.getpass("PIN: ")
        auth = client.login(pin)
        if not auth.get("success"):
            print("❌ Logowanie nieudane. Zły PIN lub brak autoryzacji.")
            sys.exit(1)
        print("✅ Logowanie pomyślne.")
    except Exception as e:
        print(f"❌ Błąd logowania: {e}")
        sys.exit(1)

    workspace_id = args.workspace
    session_id = f"cli-{int(time.time())}"

    def callback(message: str) -> dict:
        try:
            resp = client.chat(message, workspace_id, cli.session_id)
            return {
                "response": resp.get("reply", "Brak odpowiedzi od serwera."),
                "tools_used": resp.get("selected_skills", []),
            }
        except Exception as e:
            return {"response": f"Błąd komunikacji z serwerem: {e}", "tools_used": []}

    cli = InteractiveCLI(
        callback=callback,
        http_client=client,
        workspace_id=workspace_id,
        session_id=session_id,
    )
    cli.run()


if __name__ == "__main__":
    main()
