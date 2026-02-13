"""orchestify inspect — View agent activity and logs."""
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.syntax import Syntax

from orchestify.core.sprint import SprintManager
from orchestify.core.agent_logger import AgentLogger
from orchestify.cli.ui.formatting import error, info

console = Console()


@click.command()
@click.option("--sprint", "-s", help="Sprint ID (default: latest)")
@click.option("--agent", "-a", help="Filter by agent ID")
@click.option("--limit", "-n", default=20, help="Number of entries to show")
@click.option("--level", type=click.Choice(["INFO", "WARN", "ERROR", "DEBUG"]),
              help="Filter by log level")
@click.option("--timeline", is_flag=True, help="Show merged timeline of all agents")
@click.option("--task", is_flag=True, help="Show current task checkpoint")
def inspect(
    sprint: Optional[str],
    agent: Optional[str],
    limit: int,
    level: Optional[str],
    timeline: bool,
    task: bool,
) -> None:
    """View agent activity, logs, and task checkpoints.

    Shows what each agent is doing, their outputs, and execution history.
    """
    repo_root = Path.cwd()
    sprint_manager = SprintManager(repo_root)

    # Find sprint
    if sprint:
        active_sprint = sprint_manager.get(sprint)
    else:
        active_sprint = sprint_manager.get_latest_sprint()

    if not active_sprint:
        error("No sprint found. Run [cyan]orchestify init[/cyan] first.")
        sys.exit(1)

    logger = AgentLogger(active_sprint.log_dir)

    if timeline:
        _show_timeline(logger, limit)
    elif task and agent:
        _show_task_checkpoint(logger, agent)
    elif agent:
        _show_agent_logs(logger, agent, limit, level)
    else:
        _show_overview(logger, active_sprint)


def _show_overview(logger: AgentLogger, sprint) -> None:
    """Show overview of all agent activity."""
    agent_ids = logger.get_all_agent_ids()

    if not agent_ids:
        console.print("[dim]No agent activity recorded yet.[/dim]")
        return

    table = Table(title=f"Agent Activity — {sprint.sprint_id}", border_style="cyan")
    table.add_column("Agent", style="cyan")
    table.add_column("Events", style="green")
    table.add_column("Last Event", style="white")
    table.add_column("Last Time", style="dim")

    for agent_id in agent_ids:
        logs = logger.get_agent_logs(agent_id)
        count = len(logs)
        last = logs[-1] if logs else {}
        table.add_row(
            agent_id,
            str(count),
            last.get("event", "—"),
            last.get("timestamp", "—")[:19],
        )

    console.print(table)
    console.print("\n[dim]Use --agent <id> to see detailed logs.[/dim]")


def _show_agent_logs(logger: AgentLogger, agent_id: str, limit: int, level: Optional[str]) -> None:
    """Show logs for a specific agent."""
    logs = logger.get_agent_logs(agent_id, limit=limit, level=level)

    if not logs:
        console.print(f"[dim]No logs found for agent '{agent_id}'.[/dim]")
        return

    table = Table(title=f"Logs — {agent_id}", border_style="cyan")
    table.add_column("Time", style="dim", no_wrap=True)
    table.add_column("Level", style="yellow", no_wrap=True)
    table.add_column("Event", style="white")
    table.add_column("Data", style="dim", max_width=50)

    for entry in logs:
        data_str = ""
        if entry.get("data"):
            data_str = str(entry["data"])[:50]

        lvl = entry.get("level", "INFO")
        lvl_style = {"ERROR": "[red]ERROR[/red]", "WARN": "[yellow]WARN[/yellow]",
                      "DEBUG": "[dim]DEBUG[/dim]"}.get(lvl, lvl)

        table.add_row(
            entry.get("timestamp", "")[:19],
            lvl_style,
            entry.get("event", ""),
            data_str,
        )

    console.print(table)


def _show_task_checkpoint(logger: AgentLogger, agent_id: str) -> None:
    """Show current task checkpoint for an agent."""
    checkpoint = logger.load_task_checkpoint(agent_id)

    if not checkpoint:
        console.print(f"[dim]No task checkpoint for agent '{agent_id}'.[/dim]")
        return

    import yaml
    yaml_str = yaml.dump(checkpoint, default_flow_style=False)
    console.print(Panel(
        Syntax(yaml_str, "yaml", theme="monokai"),
        title=f"Task Checkpoint — {agent_id}",
        border_style="cyan",
    ))


def _show_timeline(logger: AgentLogger, limit: int) -> None:
    """Show merged timeline of all agents."""
    entries = logger.get_timeline(limit=limit)

    if not entries:
        console.print("[dim]No activity recorded yet.[/dim]")
        return

    table = Table(title="Activity Timeline", border_style="cyan")
    table.add_column("Time", style="dim", no_wrap=True)
    table.add_column("Agent", style="cyan", no_wrap=True)
    table.add_column("Event", style="white")

    for entry in entries:
        table.add_row(
            entry.get("timestamp", "")[:19],
            entry.get("agent_id", "?"),
            entry.get("event", ""),
        )

    console.print(table)
