"""orchestify stop / resume — Sprint lifecycle management."""
import os
import signal
import sys
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel

from orchestify.core.sprint import SprintManager
from orchestify.cli.commands._db_helper import get_db
from orchestify.cli.ui.formatting import error, success, warn

console = Console()


@click.command()
@click.option("--sprint", "-s", help="Sprint ID to stop (default: active)")
@click.option("--force", is_flag=True, help="Force stop even if process is unresponsive")
def stop(sprint: Optional[str], force: bool) -> None:
    """Stop/pause the current running sprint."""
    db = get_db()
    sprint_manager = SprintManager(db)

    if sprint:
        active_sprint = sprint_manager.get(sprint)
    else:
        active_sprint = sprint_manager.get_active_sprint()

    if not active_sprint:
        warn("No running sprint found.")
        return

    state = active_sprint.load_state()
    pid = state.get("pid")

    if pid and pid != os.getpid():
        try:
            if force:
                os.kill(pid, signal.SIGKILL)
                console.print(f"[red]Force killed process {pid}.[/red]")
            else:
                os.kill(pid, signal.SIGTERM)
                console.print(f"Sent stop signal to process {pid}.")
        except ProcessLookupError:
            pass
        except PermissionError:
            error(f"Permission denied to stop process {pid}.")
            return

    sprint_manager.pause(active_sprint.sprint_id)
    success(f"Sprint {active_sprint.sprint_id} paused.")
    console.print(f"Resume with: [cyan]orchestify resume -s {active_sprint.sprint_id}[/cyan]")


@click.command()
@click.option("--sprint", "-s", help="Sprint ID to resume (default: latest paused)")
def resume(sprint: Optional[str]) -> None:
    """Resume a paused sprint."""
    db = get_db()
    sprint_manager = SprintManager(db)

    if sprint:
        target_sprint = sprint_manager.get(sprint)
    else:
        paused = sprint_manager.list_sprints(status="paused")
        target_sprint = paused[-1] if paused else None

    if not target_sprint:
        warn("No paused sprint found to resume.")
        return

    state = target_sprint.load_state()
    if state.get("status") != "paused":
        warn(f"Sprint {target_sprint.sprint_id} is not paused (status: {state.get('status')}).")
        return

    sprint_manager.resume(target_sprint.sprint_id)

    console.print(Panel(
        f"[bold green]Sprint resumed![/bold green]\n\n"
        f"Sprint: [bold cyan]{target_sprint.sprint_id}[/bold cyan]\n"
        f"Goal: {state.get('prompt', 'N/A')}\n"
        f"Epic: {state.get('epic_id', 'N/A')}\n\n"
        f"Run [cyan]orchestify start -s {target_sprint.sprint_id}[/cyan] to continue execution.",
        border_style="green",
    ))
