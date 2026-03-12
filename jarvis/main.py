"""
JARVIS - Autonomous AI PC Assistant
Entry point: initializes all layers and starts the system.
"""
import os
import sys
import time
import threading
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

load_dotenv()
console = Console()


def print_banner():
    banner = Text()
    banner.append("  ██╗ █████╗ ██████╗ ██╗   ██╗██╗███████╗\n", style="bold cyan")
    banner.append("  ██║██╔══██╗██╔══██╗██║   ██║██║██╔════╝\n", style="bold cyan")
    banner.append("  ██║███████║██████╔╝██║   ██║██║███████╗\n", style="bold cyan")
    banner.append("  ██║██╔══██║██╔══██╗╚██╗ ██╔╝██║╚════██║\n", style="bold cyan")
    banner.append("  ██║██║  ██║██║  ██║ ╚████╔╝ ██║███████║\n", style="bold cyan")
    banner.append("  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝  ╚═══╝  ╚═╝╚══════╝\n", style="bold cyan")
    banner.append("  Autonomous AI PC Assistant\n", style="dim white")
    banner.append("  Powered by LLaMA 3 + CrewAI + Playwright\n", style="dim white")
    console.print(Panel(banner, border_style="cyan"))


def check_services():
    """Check that all required services are available."""
    checks = {}

    # Check Ollama
    try:
        import requests
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        r = requests.get(f"{base_url}/api/tags", timeout=3)
        checks["Ollama"] = ("✓", "green") if r.status_code == 200 else ("✗", "red")
    except Exception:
        checks["Ollama"] = ("✗ (not running — start with: ollama serve)", "red")

    # Check ChromaDB path
    chroma_path = os.getenv("CHROMA_DB_PATH", "./jarvis/.chromadb")
    os.makedirs(chroma_path, exist_ok=True)
    checks["ChromaDB"] = ("✓", "green")

    # Check Neo4j
    try:
        from neo4j import GraphDatabase
        uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        user = os.getenv("NEO4J_USER", "neo4j")
        pwd = os.getenv("NEO4J_PASSWORD", "password")
        driver = GraphDatabase.driver(uri, auth=(user, pwd))
        driver.verify_connectivity()
        driver.close()
        checks["Neo4j"] = ("✓", "green")
    except Exception as e:
        checks["Neo4j"] = (f"✗ (not connected: {e})", "red")

    # Check Tesseract
    tesseract_path = os.getenv("TESSERACT_PATH", r"C:\Program Files\Tesseract-OCR\tesseract.exe")
    if os.path.exists(tesseract_path):
        checks["Tesseract OCR"] = ("✓", "green")
    else:
        checks["Tesseract OCR"] = ("✗ (not found — vision disabled)", "yellow")

    console.print("\n[bold white]Service Status:[/bold white]")
    for service, (status, color) in checks.items():
        console.print(f"  [{color}]{status}[/{color}]  {service}")
    console.print()
    return checks


def start_telegram_mode():
    """Start JARVIS in Telegram mode."""
    from jarvis.interfaces.telegram_api import TelegramAPI
    from jarvis.ai_engine.intent_parser import IntentParser
    from jarvis.agents.crew_manager import CrewManager

    console.print("[cyan]Starting Telegram Bot Interface...[/cyan]")
    parser = IntentParser()
    crew = CrewManager()
    
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token or token == "your_token_here":
        console.print("[red]Error: TELEGRAM_BOT_TOKEN not found in .env file.[/red]")
        console.print("[yellow]Please talk to @BotFather on Telegram to get a token.[/yellow]")
        sys.exit(1)
        
    tg_api = TelegramAPI(token=token, parser=parser, crew=crew)
    console.print("[green]Telegram Bot is active and listening for messages...[/green]\n")
    tg_api.start()


def start_cli_mode():
    """Start JARVIS in CLI mode."""
    from jarvis.interfaces.cli_interface import CLIInterface
    from jarvis.ai_engine.intent_parser import IntentParser
    from jarvis.agents.crew_manager import CrewManager

    console.print("[cyan]Starting CLI interface...[/cyan]\n")
    parser = IntentParser()
    crew = CrewManager()
    cli = CLIInterface(parser=parser, crew=crew)
    cli.start()


def main():
    print_banner()
    checks = check_services()

    # Determine mode from args
    mode = "cli"
    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()
    else:
        console.print("[bold yellow]Select mode:[/bold yellow]")
        console.print("  [1] Telegram Bot (default)")
        console.print("  [2] CLI (terminal mode)")
        choice = input("\nEnter choice (1/2, default=1): ").strip()
        mode = "telegram" if choice in ("1", "") else "cli"

    console.print()

    if mode == "telegram":
        start_telegram_mode()
    else:
        # Start Flask status server in background thread for CLI mode
        from jarvis.server import create_app
        app = create_app()
        server_thread = threading.Thread(
            target=lambda: app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False),
            daemon=True
        )
        server_thread.start()
        console.print("[dim]Status server running at http://localhost:5000/status[/dim]\n")
        start_cli_mode()


if __name__ == "__main__":
    main()
