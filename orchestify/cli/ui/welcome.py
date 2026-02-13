"""Welcome screen and branding for orchestify CLI."""
import sys
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.columns import Columns

from orchestify import __version__

console = Console()

LOGO = r"""
   ___           _               _   _  __
  / _ \ _ __ ___| |__   ___  ___| |_(_)/ _|_   _
 | | | | '__/ __| '_ \ / _ \/ __| __| | |_| | | |
 | |_| | | | (__| | | |  __/\__ \ |_| |  _| |_| |
  \___/|_|  \___|_| |_|\___||___/\__|_|_|  \__, |
                                            |___/
"""


def show_welcome():
    """Display the welcome screen."""
    logo_text = Text(LOGO, style="bold cyan")

    info_lines = [
        f"[bold white]Agent Behavior Development (ABD) Engine[/bold white]",
        f"[dim]Version {__version__}[/dim]",
        "",
        "[bold yellow]Quick Start:[/bold yellow]",
        "  [cyan]orchestify install[/cyan]    Setup global configuration",
        "  [cyan]orchestify init[/cyan]       Initialize project sprint",
        "  [cyan]orchestify plan[/cyan]       Plan with TPM agent",
        "  [cyan]orchestify start[/cyan]      Run orchestration pipeline",
        "",
        "[bold yellow]Management:[/bold yellow]",
        "  [cyan]orchestify status[/cyan]     View sprint status",
        "  [cyan]orchestify inspect[/cyan]    View agent activity",
        "  [cyan]orchestify memory[/cyan]     Manage Contextify memory",
        "  [cyan]orchestify stop[/cyan]       Pause current sprint",
        "  [cyan]orchestify resume[/cyan]     Resume paused sprint",
        "",
        "[dim]Run [cyan]orchestify --help[/cyan] for full command reference.[/dim]",
    ]

    console.print(Panel(
        "\n".join(info_lines),
        title=f"[bold cyan]Orchestify v{__version__}[/bold cyan]",
        subtitle="[dim]Behavior-over-Code Paradigm[/dim]",
        border_style="cyan",
        padding=(1, 2),
    ))


def show_version():
    """Display version info."""
    console.print(f"[cyan]orchestify[/cyan] version [bold]{__version__}[/bold]")
