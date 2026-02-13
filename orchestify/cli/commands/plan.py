"""orchestify plan — Interactive TPM planning session."""
import asyncio
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.markdown import Markdown

from orchestify.core.sprint import SprintManager
from orchestify.core.config import load_config
from orchestify.core.agent_logger import AgentLogger
from orchestify.cli.ui.formatting import error, success, info, warn

console = Console()


@click.command()
@click.option("--sprint", "-s", help="Sprint ID to plan for (default: latest)")
@click.option("--prompt", "-p", help="Initial planning prompt")
@click.option("--non-interactive", is_flag=True, help="Run without user interaction")
def plan(sprint: Optional[str], prompt: Optional[str], non_interactive: bool) -> None:
    """Start an interactive TPM planning session.

    Opens a conversation with the TPM agent to break down your goal
    into an epic with actionable issues.
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

    # Get initial prompt
    state = active_sprint.load_state()
    initial_prompt = prompt or state.get("prompt")

    if not initial_prompt and not non_interactive:
        console.print(Panel(
            "[bold cyan]TPM Planning Session[/bold cyan]\n\n"
            f"Sprint: [bold]{active_sprint.sprint_id}[/bold]\n"
            "Describe your goal and the TPM agent will break it down\n"
            "into an actionable epic with issues.",
            border_style="cyan",
        ))
        initial_prompt = Prompt.ask("\n[bold cyan]What would you like to build?[/bold cyan]")

    if not initial_prompt:
        error("No prompt provided. Use --prompt or provide one interactively.")
        sys.exit(1)

    # Update sprint state
    state["prompt"] = initial_prompt
    active_sprint.save_state(state)

    # Initialize logger
    agent_logger = AgentLogger(active_sprint.log_dir)

    console.print()
    console.print(Panel(
        f"[bold yellow]TPM Agent Planning[/bold yellow]\n\n"
        f"Goal: {initial_prompt}\n\n"
        f"[dim]The TPM agent will analyze your request and create an epic plan.\n"
        f"This requires a configured LLM provider with a valid API key.[/dim]",
        border_style="yellow",
    ))

    # Log the planning start
    agent_logger.log("tpm", "planning_started", {
        "sprint_id": active_sprint.sprint_id,
        "prompt": initial_prompt,
    })

    # Check if we have a valid provider configured
    tpm_config = None
    if hasattr(config, "agents") and hasattr(config.agents, "agents"):
        tpm_config = config.agents.agents.get("tpm") or config.agents.agents.get("planner")

    if not tpm_config:
        warn("TPM agent not configured in agents.yaml.")
        console.print(
            "[dim]To use the TPM agent, configure it in config/agents.yaml\n"
            "and ensure you have a valid API key.[/dim]"
        )
        _generate_mock_plan(active_sprint, initial_prompt, agent_logger)
        return

    # Try to run actual TPM agent
    try:
        asyncio.run(_run_tpm_session(
            config, active_sprint, initial_prompt, agent_logger, non_interactive
        ))
    except KeyboardInterrupt:
        console.print("\n[yellow]Planning session interrupted.[/yellow]")
        agent_logger.log("tpm", "planning_interrupted")
    except Exception as e:
        warn(f"TPM agent execution failed: {e}")
        console.print("[dim]Falling back to template-based planning...[/dim]")
        _generate_mock_plan(active_sprint, initial_prompt, agent_logger)


async def _run_tpm_session(config, sprint, prompt, logger, non_interactive):
    """Run the actual TPM agent session."""
    from orchestify.core.engine import OrchestrifyEngine
    from orchestify.core.state import StateManager

    state_manager = StateManager(sprint.sprint_dir)
    engine = OrchestrifyEngine(
        config={"max_self_fixes": 3},
        state_manager=state_manager,
        provider_registry={},
        memory_client=None,
    )

    result = await engine.run_phase("tpm", input_text=prompt)

    if result.get("success"):
        epic_id = result.get("epic_id", "epic-001")

        # Update sprint state
        state = sprint.load_state()
        state["epic_id"] = epic_id
        state["status"] = "planned"
        sprint.save_state(state)

        logger.log("tpm", "planning_complete", {"epic_id": epic_id})
        success(f"Epic {epic_id} planned successfully!")
        console.print(f"\nRun [cyan]orchestify start[/cyan] to begin execution.")
    else:
        error(f"Planning failed: {result.get('error', 'Unknown error')}")


def _generate_mock_plan(sprint, prompt, logger):
    """Generate a template plan when TPM agent is not available."""
    plan_text = f"""# Epic Plan

## Goal
{prompt}

## Issues (Template)

### Issue 1: Project Setup
- Set up project structure and dependencies
- Configure development environment

### Issue 2: Core Implementation
- Implement main functionality based on the goal
- Write unit tests

### Issue 3: Integration & Testing
- Integration testing
- End-to-end validation

### Issue 4: Documentation & Polish
- Update documentation
- Code cleanup and final review

---
*This is a template plan. Configure a TPM agent for AI-powered planning.*
"""

    # Save plan to sprint artifacts
    plan_file = sprint.artifacts_dir / "plan.md"
    plan_file.write_text(plan_text)

    # Update sprint state
    state = sprint.load_state()
    state["status"] = "planned"
    state["epic_id"] = "epic-001"
    state["issues_total"] = 4
    sprint.save_state(state)

    logger.log("tpm", "template_plan_generated", {
        "plan_file": str(plan_file),
        "issues_count": 4,
    })

    console.print(Markdown(plan_text))
    success(f"\nTemplate plan saved to {plan_file}")
    console.print("Run [cyan]orchestify start[/cyan] to begin execution.")
