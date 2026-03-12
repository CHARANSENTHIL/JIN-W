"""
JARVIS CLI Interface — terminal-based REPL for testing without WhatsApp.
"""
import os
import time
from rich.console import Console
from rich.text import Text
from rich.panel import Panel

console = Console()


class CLIInterface:
    def __init__(self, parser, crew):
        self.parser = parser
        self.crew = crew
        self._running = False
        self.multiline_buffer = []
        self.last_message_time = None
        self.multiline_timeout = float(os.getenv("MULTILINE_TIMEOUT", "2.5"))

    def _print_result(self, result: dict):
        """Pretty-print an execution result."""
        status = result.get("status", "unknown")
        message = result.get("message", "")
        data = result.get("data", "")

        color = "green" if status == "success" else "red" if status == "error" else "yellow"
        icon = "✅" if status == "success" else "❌" if status == "error" else "⚠️"

        output = f"{icon} {message}"
        if data:
            output += f"\n{data}"

        console.print(Panel(output, border_style=color, title=f"[{color}]{status.upper()}[/{color}]"))

    def start(self):
        """Start the interactive CLI loop."""
        console.print(Panel(
            "[bold cyan]JARVIS CLI Mode[/bold cyan]\n"
            "[dim]Type commands. Use empty line or wait 2.5s to submit multiline blocks.[/dim]\n"
            "[dim]Commands: 'exit' to quit, 'help' for examples[/dim]",
            border_style="cyan"
        ))

        self._running = True
        buffer = []

        print()
        while self._running:
            try:
                line = input("[bold]> [/bold]" if False else "> ").strip()

                if line.lower() in ("exit", "quit", "q"):
                    console.print("[yellow]JARVIS shutting down...[/yellow]")
                    break

                if line.lower() == "help":
                    self._show_help()
                    continue

                if line == "":
                    # Empty line = flush buffer
                    if buffer:
                        self._process_buffer(buffer)
                        buffer = []
                    continue

                buffer.append(line)

                # Auto-submit single-line commands (no continuation)
                # Allow multiline by pressing Enter twice
                # Check for obvious single-line intent keywords
                INSTANT_KEYWORDS = [
                    "what is", "open ", "close ", "show me", "check ", "status",
                    "cpu", "gpu", "ram", "disk", "screenshot", "list "
                ]
                is_instant = any(line.lower().startswith(kw) for kw in INSTANT_KEYWORDS)
                if is_instant and len(buffer) == 1:
                    self._process_buffer(buffer)
                    buffer = []

            except KeyboardInterrupt:
                console.print("\n[yellow]Use 'exit' to quit JARVIS.[/yellow]")
                continue
            except EOFError:
                break

        console.print("[dim]JARVIS has stopped.[/dim]")

    def _process_buffer(self, lines: list):
        """Parse and execute a collected set of command lines."""
        full_command = "\n".join(lines)
        console.print(f"\n[dim]Processing: {repr(full_command[:80])}...[/dim]" if len(full_command) > 80 else f"\n[dim]Processing: {repr(full_command)}[/dim]")

        try:
            intent = self.parser.parse(full_command)
            console.print(f"[dim]Intent: {intent.get('intent')} | Agent: {intent.get('agent_needed')}[/dim]")
            result = self.crew.execute(intent)
            self._print_result(result)
        except Exception as e:
            console.print(f"[red]❌ Error: {e}[/red]")
        print()

    def _show_help(self):
        """Show usage examples."""
        examples = """[bold cyan]JARVIS CLI Examples:[/bold cyan]

[yellow]Single commands:[/yellow]
  what is my cpu usage
  open vscode
  close notepad
  take a screenshot
  create file d:/test.py with hello world python program

[yellow]Multiline commands (press Enter after each line, then again to submit):[/yellow]
  open vscode
  create file main.py
  write bubble sort in python
  run it

[yellow]Browser tasks:[/yellow]
  open leetcode and solve the daily problem
  book avengers doomsday ticket saturday 7pm
  create linkedin post about my coding progress today

[yellow]System:[/yellow]
  what is my gpu temperature
  show me running processes
  how much disk space do i have
"""
        console.print(Panel(examples, border_style="dim"))
