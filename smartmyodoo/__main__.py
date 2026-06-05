import sys
import os
import argparse
import subprocess
import uvicorn
from smartmyodoo.core.database import backup_before_migrate


def run_migrations():
    """Wykonywanie kopii zapasowej i aktualizacja schematu bazy danych."""
    print("Pre-migration backup...")
    backup_before_migrate()
    print("Running database migrations...")
    env = os.environ.copy()
    try:
        subprocess.run(["alembic", "upgrade", "head"], env=env, check=True)
        print("Migrations completed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Migration failed: {e}", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError:
        print("Alembic not found. Is it installed?", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="SmartMyOdoo CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Serve command
    serve_parser = subparsers.add_parser("serve", help="Run the FastAPI server")
    serve_parser.add_argument("--host", default="127.0.0.1", help="Host serwera")
    serve_parser.add_argument("--port", type=int, default=5000, help="Port serwera")

    # MCP command
    subparsers.add_parser("mcp", help="Run the MCP server (Odoo Tools)")

    # Vault command
    vault_parser = subparsers.add_parser("vault", help="Vault management tools")
    vault_parser.add_argument(
        "action", choices=["init", "reset-pin"], help="Vault action"
    )

    args = parser.parse_args()

    # Default to serve if no command provided
    command = args.command or "serve"

    if command == "serve":
        run_migrations()
        print("Starting FastAPI server...")
        uvicorn.run("smartmyodoo.api:app", host=args.host, port=args.port, reload=False)

    elif command == "mcp":
        from smartmyodoo.mcp.server import serve as mcp_serve

        mcp_serve()

    elif command == "vault":
        print(f"Vault action {args.action} not yet implemented via CLI.")


if __name__ == "__main__":
    main()
