import argparse
import sys
import time

from smartmyodoo.cli import InteractiveCLI
from smartmyodoo.http_client import SmartMyOdooClient


def main():
    parser = argparse.ArgumentParser(description="SmartMyOdoo CLI (Thin Client)")
    parser.add_argument(
        "--url",
        type=str,
        default="http://127.0.0.1:8000",
        help="URL of the FastAPI server",
    )
    parser.add_argument("--workspace", type=str, default="default", help="Workspace ID")
    args = parser.parse_args()

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
