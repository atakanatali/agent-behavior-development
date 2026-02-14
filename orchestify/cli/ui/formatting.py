"""Shared formatting utilities for CLI output."""
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn

console = Console()


def error(message: str) -> None:
    """Print error message."""
    console.print(f"[bold red]Error:[/bold red] {message}")


def warn(message: str) -> None:
    """Print warning message."""
    console.print(f"[yellow]Warning:[/yellow] {message}")


def success(message: str) -> None:
    """Print success message."""
    console.print(f"[green]{message}[/green]")


def info(message: str) -> None:
    """Print info message."""
    console.print(f"[cyan]{message}[/cyan]")


def step(number: int, total: int, message: str) -> None:
    """Print a step indicator."""
    console.print(f"  [dim][{number}/{total}][/dim] {message}")


def section_panel(content: str, title: str, style: str = "cyan") -> None:
    """Print a section panel."""
    console.print(Panel(content, title=title, border_style=style, padding=(0, 1)))


def create_progress() -> Progress:
    """Create a standard progress bar."""
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        console=console,
    )


def agent_table(agents: dict) -> Table:
    """Create an agent status table."""
    table = Table(title="Registered Agents", border_style="cyan")
    table.add_column("Agent", style="cyan", no_wrap=True)
    table.add_column("Model", style="green")
    table.add_column("Provider", style="magenta")
    table.add_column("Mode", style="yellow")
    table.add_column("Temp", style="dim")

    for name, agent in agents.items():
        table.add_row(
            name,
            agent.get("model", "—"),
            agent.get("provider", "—"),
            agent.get("mode", "—"),
            str(agent.get("temperature", "—")),
        )

    return table
