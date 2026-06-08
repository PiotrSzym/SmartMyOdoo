import time

from prompt_toolkit import PromptSession
from prompt_toolkit.styles import Style
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table


class InteractiveCLI:
    def __init__(
        self, callback, http_client=None, workspace_id="default", session_id=None
    ):
        self.console = Console()
        self.callback = callback
        self.http_client = http_client
        self.workspace_id = workspace_id
        self.session_id = session_id or f"cli-{int(time.time())}"
        self.style = Style.from_dict(
            {
                "prompt": "#00ff00 bold",
            }
        )
        self.session = PromptSession(style=self.style)

    def print_agent_response(self, text: str, tools_used: list | None = None):
        if tools_used:
            self.console.print(
                f"[dim italic]Tools used: {', '.join(tools_used)}[/dim italic]"
            )
        md = Markdown(text)
        self.console.print(Panel(md, title="SmartMyOdoo Agent", border_style="blue"))

    def print_error(self, text: str):
        self.console.print(f"[bold red]Error:[/bold red] {text}")

    def _show_previous_sessions(self):
        """Wyświetla listę poprzednich sesji (Smart Context) pobraną z API."""
        if not self.http_client:
            return

        try:
            sessions = self.http_client.list_sessions(self.workspace_id, limit=5)
        except Exception as e:
            self.console.print(f"[dim red]Nie udało się pobrać sesji: {e}[/dim red]\n")
            return
        if not sessions:
            self.console.print(
                "[dim]Brak wcześniejszych sesji w tym workspace.[/dim]\n"
            )
            return

        table = Table(title="📋 Ostatnie sesje", border_style="dim", show_lines=False)
        table.add_column("#", style="dim", width=3)
        table.add_column("Sesja", style="cyan", width=12)
        table.add_column("Preview", style="white")
        table.add_column("Msgs", style="green", width=5)
        table.add_column("Ostatnia aktywność", style="dim", width=20)

        for i, s in enumerate(sessions, 1):
            table.add_row(
                str(i),
                s["session_id"][:10] + "...",
                s["preview"] or "[dim]—[/dim]",
                str(s["message_count"]),
                s["last_activity"][:16] if s["last_activity"] else "—",
            )

        self.console.print(table)

        # Zapytaj czy kontynuować ostatnią sesję
        try:
            choice = (
                self.session.prompt(
                    [("class:prompt", "Kontynuować ostatnią sesję? (y/N/numer): ")]
                )
                .strip()
                .lower()
            )

            if choice == "y" and sessions:
                self.session_id = sessions[0]["session_id"]
                self.console.print(
                    f"[green]✓ Wznowiono sesję: {self.session_id[:10]}...[/green]\n"
                )
            elif choice.isdigit() and 1 <= int(choice) <= len(sessions):
                self.session_id = sessions[int(choice) - 1]["session_id"]
                self.console.print(
                    f"[green]✓ Załadowano sesję: {self.session_id[:10]}...[/green]\n"
                )
            else:
                self.console.print(
                    f"[cyan]→ Nowa sesja: {self.session_id[:10]}...[/cyan]\n"
                )
        except (KeyboardInterrupt, EOFError):
            pass

    def run(self):
        self.console.print(
            Panel(
                "[bold green]Witaj w SmartMyOdoo CLI![/bold green]\n"
                f"[dim]Workspace: [cyan]{self.workspace_id}[/cyan] | "
                f"Session: [cyan]{self.session_id[:10]}...[/cyan][/dim]\n"
                "[dim]Wpisz 'exit' aby wyjść | '/sessions' aby zobaczyć historię[/dim]",
                title="🤖 SmartMyOdoo Agent",
                border_style="bright_blue",
            )
        )

        self._show_previous_sessions()

        while True:
            try:
                user_input = self.session.prompt([("class:prompt", "You: ")])
                if user_input.strip().lower() in ["exit", "quit"]:
                    break
                if not user_input.strip():
                    continue

                # Komendy specjalne
                if user_input.strip() == "/sessions":
                    self._show_previous_sessions()
                    continue

                # Oznaczenie że system pracuje
                if hasattr(self.http_client, "chat_stream"):
                    import asyncio
                    from rich.live import Live
                    from rich.console import Group
                    from rich.text import Text

                    async def run_stream():
                        full_text = ""
                        logs_text = ""

                        def get_renderable():
                            items = []
                            if logs_text:
                                items.append(
                                    Text(logs_text.strip(), style="dim italic")
                                )
                            items.append(
                                Panel(
                                    Markdown(full_text),
                                    title="SmartMyOdoo Agent",
                                    border_style="blue",
                                )
                            )
                            return Group(*items)

                        with Live(
                            get_renderable(),
                            refresh_per_second=15,
                            console=self.console,
                        ) as live:
                            generator = self.http_client.chat_stream(
                                message=user_input,
                                workspace_id=self.workspace_id,
                                session_id=self.session_id,
                            )
                            async for chunk in generator:
                                if chunk["type"] == "token":
                                    full_text += chunk["content"]
                                    live.update(get_renderable())
                                elif chunk["type"] == "log":
                                    logs_text += f"⚙️ {chunk['content']}\n"
                                    live.update(get_renderable())
                                elif chunk["type"] == "error":
                                    logs_text += f"❌ Błąd: {chunk['content']}\n"
                                    live.update(get_renderable())
                                elif chunk["type"] == "done":
                                    break

                    asyncio.run(run_stream())
                else:
                    with self.console.status(
                        "[bold cyan]Agent myśli...[/bold cyan]", spinner="dots"
                    ):
                        result = self.callback(user_input)

                    self.print_agent_response(
                        result.get("response", ""), result.get("tools_used", [])
                    )

            except KeyboardInterrupt:
                continue
            except EOFError:
                break
            except Exception as e:
                self.print_error(str(e))
