"""orchestify status — Show current pipeline/sprint status."""
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from orchestify.core.sprint import SprintManager
from orchestify.core.config import load_config
from orchestify.cli.commands._db_helper import get_db
from orchestify.cli.ui.formatting import error

console = Console()

STATUS_ICONS = {
    "created": "[dim]○[/dim]",
    "planned": "[blue]◑[/blue]",
    "running": "[yellow]●[/yellow]",
    "paused": "[yellow]◎[/yellow]",
    "complete": "[green]●[/green]",
    "completed": "[green]●[/green]",
    "error": "[red]●[/red]",
}


@click.command()
@click.option("--sprint", "-s", help="Show status for specific sprint")
@click.option("--all", "show_all", is_flag=True, help="Show all sprints")
def status(sprint: Optional[str], show_all: bool) -> None:
    """Show current sprint and pipeline status."""
    db = get_db()
    sprint_manager = SprintManager(db)

    if sprint:
        s = sprint_manager.get(sprint)
        if not s:
            error(f"Sprint '{sprint}' not found.")
            sys.exit(1)
        _show_sprint_detail(s)
    elif show_all:
        _show_all_sprints(sprint_manager)
    else:
        repo_root = Path.cwd()
        _show_overview(repo_root, sprint_manager)


def _show_overview(repo_root: Path, sprint_manager: SprintManager) -> None:
    """Show project overview with latest sprint."""
    config_dir = repo_root / "config"

    if config_dir.exists():
        try:
            config = load_config(config_dir)
            console.print(Panel(
                f"Project: [bold]{config.project.name}[/bold]\n"
                f"Repo: {config.project.repo}\n"
                f"Branch: {config.project.main_branch}",
                title="Project",
                border_style="cyan",
            ))
        except Exception:
            console.print("[dim]Config directory found but unable to load.[/dim]")
    else:
        console.print("[yellow]No project config found. Run [cyan]orchestify init[/cyan] first.[/yellow]")
        return

    latest = sprint_manager.get_latest_sprint()
    if latest:
        _show_sprint_detail(latest)
    else:
        console.print("[dim]No sprints found. Run [cyan]orchestify init[/cyan] to create one.[/dim]")


def _show_sprint_detail(sprint) -> None:
    """Show detailed sprint status."""
    state = sprint.load_state()
    status_val = state.get("status", "unknown")
    icon = STATUS_ICONS.get(status_val, "[dim]?[/dim]")

    lines = [
        f"Status: {icon} [bold]{status_val}[/bold]",
        f"Created: {state.get('created_at', 'N/A')}",
    ]

    if state.get("started_at"):
        lines.append(f"Started: {state['started_at']}")
    if state.get("paused_at"):
        lines.append(f"Paused: {state['paused_at']}")
    if state.get("completed_at"):
        lines.append(f"Completed: {state['completed_at']}")
    if state.get("prompt"):
        lines.append(f"Goal: {state['prompt'][:80]}")
    if state.get("epic_id"):
        lines.append(f"Epic: {state['epic_id']}")

    issues_total = state.get("issues_total", 0)
    issues_done = state.get("issues_done", 0)
    if issues_total > 0:
        lines.append(f"Progress: {issues_done}/{issues_total} issues")

    if state.get("pid"):
        lines.append(f"PID: {state['pid']}")

    if state.get("error"):
        lines.append(f"[red]Error: {state['error']}[/red]")

    console.print(Panel(
        "\n".join(lines),
        title=f"Sprint: [bold cyan]{sprint.sprint_id}[/bold cyan]",
        border_style="cyan" if status_val != "error" else "red",
    ))


def _show_all_sprints(sprint_manager: SprintManager) -> None:
    """Show all sprints in a table."""
    sprints = sprint_manager.list_sprints()

    if not sprints:
        console.print("[dim]No sprints found.[/dim]")
        return

    table = Table(title="All Sprints", border_style="cyan")
    table.add_column("Sprint ID", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Created", style="dim")
    table.add_column("Goal", style="white", max_width=40)

    for s in reversed(sprints):
        state = s.load_state()
        status_val = state.get("status", "unknown")
        icon = STATUS_ICONS.get(status_val, "?")
        prompt = state.get("prompt", "—")
        if prompt and len(prompt) > 40:
            prompt = prompt[:37] + "..."

        table.add_row(
            s.sprint_id,
            f"{icon} {status_val}",
            state.get("created_at", "—")[:19],
            prompt or "—",
        )

    console.print(table)
