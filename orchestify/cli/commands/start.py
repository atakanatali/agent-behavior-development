"""orchestify start — Run the full orchestration pipeline."""
import asyncio
import os
import sys
import time
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table

from orchestify.core.sprint import SprintManager
from orchestify.core.config import load_config
from orchestify.core.state import StateManager, EpicStatus, IssueStatus
from orchestify.core.agent_logger import AgentLogger
from orchestify.cli.ui.formatting import error, success, info, warn
from orchestify.cli.ui.streaming import PipelineDisplay

console = Console()


@click.command()
@click.option("--sprint", "-s", help="Sprint ID to run (default: latest)")
@click.option("--phase", type=click.Choice(["tpm", "architect", "engineer", "reviewer", "qa"]),
              help="Start from a specific phase")
@click.option("--issue", type=int, help="Run specific issue only")
@click.option("--dry-run", is_flag=True, help="Simulate execution without making changes")
def start(sprint: Optional[str], phase: Optional[str], issue: Optional[int], dry_run: bool) -> None:
    """Run the ABD orchestration pipeline.

    Executes the full pipeline: TPM → Architect → Issue Loop → Complete.
    Shows live progress with Rich streaming display.
    """
    repo_root = Path.cwd()
    config_dir = repo_root / "config"

    if not config_dir.exists():
        error("Config directory not found. Run [cyan]orchestify init[/cyan] first.")
        sys.exit(1)

    # Find sprint
    sprint_manager = SprintManager(repo_root)

    if sprint:
        active_sprint = sprint_manager.get(sprint)
        if not active_sprint:
            error(f"Sprint '{sprint}' not found.")
            sys.exit(1)
    else:
        active_sprint = sprint_manager.get_latest_sprint()
        if not active_sprint:
            error("No sprint found. Run [cyan]orchestify init[/cyan] first.")
            sys.exit(1)

    # Load config
    try:
        config = load_config(config_dir)
    except Exception as e:
        error(f"Failed to load config: {e}")
        sys.exit(1)

    # Check sprint state
    state = active_sprint.load_state()
    if state.get("status") == "running":
        warn(f"Sprint {active_sprint.sprint_id} is already running (PID: {state.get('pid')}).")
        console.print("Use [cyan]orchestify stop[/cyan] to stop it first.")
        return

    if state.get("status") == "complete":
        warn(f"Sprint {active_sprint.sprint_id} is already complete.")
        console.print("Use [cyan]orchestify init[/cyan] to create a new sprint.")
        return

    # Display pipeline info
    display = PipelineDisplay()
    console.print(Panel(
        f"[bold cyan]Starting Pipeline[/bold cyan]\n\n"
        f"Sprint: [bold]{active_sprint.sprint_id}[/bold]\n"
        f"Goal: {state.get('prompt', 'N/A')}\n"
        f"Epic: {state.get('epic_id', 'TBD')}\n"
        + (f"Phase: {phase}\n" if phase else "")
        + (f"Issue: {issue}\n" if issue else "")
        + (f"[yellow]DRY RUN[/yellow]\n" if dry_run else ""),
        border_style="cyan",
    ))

    if dry_run:
        _dry_run_pipeline(active_sprint, config, display)
        return

    # Update sprint state
    state["status"] = "running"
    state["started_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    state["pid"] = os.getpid()
    active_sprint.save_state(state)

    # Initialize logger
    agent_logger = AgentLogger(active_sprint.log_dir)
    agent_logger.log("pipeline", "pipeline_started", {
        "sprint_id": active_sprint.sprint_id,
        "phase": phase,
        "issue": issue,
    })

    # Run pipeline
    try:
        asyncio.run(_run_pipeline(
            config, active_sprint, agent_logger, display, phase, issue
        ))
    except KeyboardInterrupt:
        console.print("\n[yellow]Pipeline interrupted. Sprint paused.[/yellow]")
        sprint_manager.pause(active_sprint.sprint_id)
        agent_logger.log("pipeline", "pipeline_interrupted")
    except Exception as e:
        error(f"Pipeline error: {e}")
        state = active_sprint.load_state()
        state["status"] = "error"
        state["error"] = str(e)
        active_sprint.save_state(state)
        agent_logger.log("pipeline", "pipeline_error", {"error": str(e)}, level="ERROR")


async def _run_pipeline(config, sprint, logger, display, start_phase, target_issue):
    """Run the full pipeline with live display."""
    from orchestify.core.engine import OrchestrifyEngine

    state_manager = StateManager(sprint.sprint_dir)

    engine = OrchestrifyEngine(
        config={
            "max_self_fixes": getattr(config, 'dev_loop', None) and config.dev_loop.max_self_fix or 5,
        },
        state_manager=state_manager,
        provider_registry={},
        memory_client=None,
    )

    # Show live display
    console.print()
    console.print(display.render())

    result = await engine.run_full_pipeline(prompt=sprint.load_state().get("prompt"))

    if result.get("success"):
        sprint_state = sprint.load_state()
        sprint_state["status"] = "complete"
        sprint_state["completed_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        sprint.save_state(sprint_state)

        logger.log("pipeline", "pipeline_complete", result)
        console.print()
        success("Pipeline completed successfully!")
    else:
        error_msg = result.get("error", "Unknown error")
        logger.log("pipeline", "pipeline_failed", {"error": error_msg}, level="ERROR")
        console.print()
        error(f"Pipeline failed: {error_msg}")


def _dry_run_pipeline(sprint, config, display):
    """Simulate pipeline execution."""
    phases = ["TPM", "Architect", "Engineer Loop", "Review", "QA", "Complete"]

    console.print()
    for i, phase_name in enumerate(phases):
        display.current_phase_idx = i
        console.print(f"  [dim][{i+1}/{len(phases)}][/dim] {phase_name}... [green]OK[/green]")
        time.sleep(0.3)

    console.print()
    success("Dry run complete. No changes were made.")
    console.print("[dim]Remove --dry-run to execute the pipeline.[/dim]")
