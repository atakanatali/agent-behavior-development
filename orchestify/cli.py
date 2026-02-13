"""Command-line interface for orchestify."""
import subprocess
import sys
from pathlib import Path
from typing import Optional

import click
from rich import print as rprint
from rich.panel import Panel
from rich.table import Table
from rich.console import Console

from orchestify.core.config import load_config, validate_config, OrchestrifyConfig

console = Console()


def _check_git_repo(path: Path = Path.cwd()) -> bool:
    """Check if current directory is a git repository."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            cwd=path,
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def _check_gh_cli() -> bool:
    """Check if gh CLI is installed."""
    try:
        result = subprocess.run(
            ["gh", "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def _create_default_configs(config_dir: Path) -> None:
    """Create default configuration files."""
    config_dir.mkdir(parents=True, exist_ok=True)

    # orchestify.yaml
    orchestify_yaml = config_dir / "orchestify.yaml"
    if not orchestify_yaml.exists():
        orchestify_yaml.write_text(
            """project:
  name: "My Project"
  repo: "owner/repo"
  main_branch: "main"
  branch_prefix: "feature/"

orchestration:
  max_review_cycles: 3
  max_qa_cycles: 3
  auto_merge: true
  sequential_issues: true

issue:
  max_changes_per_issue: 20
  language: "en"
  require_agent_directive: true
  require_done_checklist: true

abd:
  scorecard_enabled: true
  recycle_mandatory: true
  evidence_required: true

dev_loop:
  build_cmd: ""
  lint_cmd: ""
  test_cmd: ""
  max_self_fix: 5
  timeout_per_command: 120
"""
        )

    # agents.yaml
    agents_yaml = config_dir / "agents.yaml"
    if not agents_yaml.exists():
        agents_yaml.write_text(
            """agents:
  executor:
    provider: anthropic
    model: claude-opus-4-6
    temperature: 0.7
    thinking: false
    mode: autonomous
    max_tokens: 8192

  reviewer:
    provider: anthropic
    model: claude-opus-4-6
    temperature: 0.5
    thinking: false
    mode: autonomous
    max_tokens: 4096

  qa:
    provider: anthropic
    model: claude-opus-4-6
    temperature: 0.7
    thinking: false
    mode: autonomous
    max_tokens: 4096

  planner:
    provider: anthropic
    model: claude-opus-4-6
    temperature: 0.5
    thinking: true
    mode: autonomous
    max_tokens: 8192

  architect:
    provider: anthropic
    model: claude-opus-4-6
    temperature: 0.6
    thinking: true
    mode: autonomous
    max_tokens: 8192

  validator:
    provider: anthropic
    model: claude-opus-4-6
    temperature: 0.3
    thinking: false
    mode: autonomous
    max_tokens: 4096

  documenter:
    provider: anthropic
    model: claude-opus-4-6
    temperature: 0.5
    thinking: false
    mode: autonomous
    max_tokens: 4096

  debugger:
    provider: anthropic
    model: claude-opus-4-6
    temperature: 0.7
    thinking: true
    mode: autonomous
    max_tokens: 8192

  synthesizer:
    provider: anthropic
    model: claude-opus-4-6
    temperature: 0.6
    thinking: true
    mode: autonomous
    max_tokens: 8192

  scorecardist:
    provider: anthropic
    model: claude-opus-4-6
    temperature: 0.3
    thinking: false
    mode: autonomous
    max_tokens: 2048

  recycler:
    provider: anthropic
    model: claude-opus-4-6
    temperature: 0.6
    thinking: true
    mode: autonomous
    max_tokens: 8192
"""
        )

    # providers.yaml
    providers_yaml = config_dir / "providers.yaml"
    if not providers_yaml.exists():
        providers_yaml.write_text(
            """providers:
  anthropic:
    type: anthropic
    api_key: ${ANTHROPIC_API_KEY}
    default_model: claude-opus-4-6
    max_tokens: 8192
    base_url: null
"""
        )

    # memory.yaml
    memory_yaml = config_dir / "memory.yaml"
    if not memory_yaml.exists():
        memory_yaml.write_text(
            """contextify:
  enabled: false
  host: "http://localhost:8080"
  protocol: "http"
  layers:
    agent:
      ttl: null
      max_entries: 1000
    epic:
      ttl: null
      max_entries: 1000
    global:
      ttl: null
      max_entries: 1000

fallback:
  type: "local_json"
  path: ".orchestify/memory/"
"""
        )


@click.group()
def cli() -> None:
    """Agent Behavior Development (ABD) — Multi-agent orchestration engine."""
    pass


@cli.command()
def init() -> None:
    """Initialize orchestify in current git repository."""
    # Check git repo
    if not _check_git_repo():
        rprint("[red]Error:[/red] Not a git repository. Run this command in a git repo.")
        sys.exit(1)

    # Check gh CLI
    if not _check_gh_cli():
        rprint("[yellow]Warning:[/yellow] GitHub CLI (gh) not found. Some features may not work.")

    config_dir = Path.cwd() / "config"
    orchestify_dir = Path.cwd() / ".orchestify"

    # Create directories
    config_dir.mkdir(parents=True, exist_ok=True)
    orchestify_dir.mkdir(parents=True, exist_ok=True)
    (orchestify_dir / "memory").mkdir(parents=True, exist_ok=True)

    # Create default config files
    _create_default_configs(config_dir)

    rprint(
        Panel(
            "[green]✓ Orchestify initialized successfully![/green]\n\n"
            f"Created config directory: [bold]{config_dir}[/bold]\n"
            f"Created .orchestify directory: [bold]{orchestify_dir}[/bold]\n\n"
            "Next steps:\n"
            "1. Edit [cyan]config/orchestify.yaml[/cyan] with your project details\n"
            "2. Update [cyan]config/agents.yaml[/cyan] if needed\n"
            "3. Run [cyan]orchestify config validate[/cyan] to verify setup\n"
            "4. Run [cyan]orchestify run[/cyan] to start the pipeline",
            title="Orchestify Init",
        )
    )


@cli.command()
@click.option("--plan", type=click.Path(), help="Path to plan file")
@click.option("--prompt", help="Custom prompt for execution")
@click.option("--phase", type=click.Choice(["plan", "execute", "review", "qa"]), help="Start from specific phase")
@click.option("--epic", type=int, help="Epic number to run")
@click.option("--issue", type=int, help="Issue number to run")
@click.option("--pr", type=int, help="Pull request number to run")
def run(
    plan: Optional[str],
    prompt: Optional[str],
    phase: Optional[str],
    epic: Optional[int],
    issue: Optional[int],
    pr: Optional[int],
) -> None:
    """Run the ABD orchestration pipeline."""
    config_dir = Path.cwd() / "config"

    if not config_dir.exists():
        rprint("[red]Error:[/red] Config directory not found. Run [cyan]orchestify init[/cyan] first.")
        sys.exit(1)

    try:
        config = load_config(config_dir)
    except Exception as e:
        rprint(f"[red]Error loading config:[/red] {str(e)}")
        sys.exit(1)

    # Display run information
    run_info = []
    if plan:
        run_info.append(f"Plan: {plan}")
    if prompt:
        run_info.append(f"Prompt: {prompt[:50]}...")
    if phase:
        run_info.append(f"Phase: {phase}")
    if epic:
        run_info.append(f"Epic: {epic}")
    if issue:
        run_info.append(f"Issue: {issue}")
    if pr:
        run_info.append(f"PR: {pr}")

    rprint(
        Panel(
            "[yellow]Pipeline execution not yet implemented[/yellow]\n\n"
            + "\n".join(run_info) if run_info else "Running with default settings",
            title="ABD Pipeline",
        )
    )


@cli.command()
@click.option("--epic", type=int, help="Show status for specific epic")
def status(epic: Optional[int]) -> None:
    """Show current pipeline status."""
    config_dir = Path.cwd() / "config"

    if not config_dir.exists():
        rprint("[red]Error:[/red] Config directory not found. Run [cyan]orchestify init[/cyan] first.")
        sys.exit(1)

    try:
        config = load_config(config_dir)
    except Exception as e:
        rprint(f"[red]Error loading config:[/red] {str(e)}")
        sys.exit(1)

    # Create status table
    table = Table(title="Pipeline Status")
    table.add_column("Component", style="cyan")
    table.add_column("Status", style="green")

    table.add_row("Project", config.project.name)
    table.add_row("Repository", config.project.repo)
    table.add_row("Main Branch", config.project.main_branch)
    table.add_row("Agents", str(len(config.agents.agents)))
    table.add_row("Providers", str(len(config.providers.providers)))

    rprint(table)

    if epic:
        rprint(f"\n[cyan]Epic {epic} status:[/cyan] [yellow]Not implemented[/yellow]")


@cli.group()
def config() -> None:
    """Configuration management commands."""
    pass


@config.command()
def validate() -> None:
    """Validate configuration files."""
    config_dir = Path.cwd() / "config"

    if not config_dir.exists():
        rprint("[red]Error:[/red] Config directory not found. Run [cyan]orchestify init[/cyan] first.")
        sys.exit(1)

    try:
        cfg = load_config(config_dir)
    except Exception as e:
        rprint(f"[red]✗ Configuration invalid:[/red] {str(e)}")
        sys.exit(1)

    warnings = validate_config(cfg)

    rprint("[green]✓ Configuration is valid[/green]")

    if warnings:
        rprint("\n[yellow]Warnings:[/yellow]")
        for warning in warnings:
            rprint(f"  • {warning}")
    else:
        rprint("\n[green]No warnings found[/green]")


@config.command()
def show() -> None:
    """Display current configuration."""
    config_dir = Path.cwd() / "config"

    if not config_dir.exists():
        rprint("[red]Error:[/red] Config directory not found. Run [cyan]orchestify init[/cyan] first.")
        sys.exit(1)

    try:
        cfg = load_config(config_dir)
    except Exception as e:
        rprint(f"[red]Error loading config:[/red] {str(e)}")
        sys.exit(1)

    # Project info
    rprint(
        Panel(
            f"Name: {cfg.project.name}\nRepo: {cfg.project.repo}\n"
            f"Main Branch: {cfg.project.main_branch}\nBranch Prefix: {cfg.project.branch_prefix}",
            title="Project",
        )
    )

    # Orchestration info
    rprint(
        Panel(
            f"Max Review Cycles: {cfg.orchestration.max_review_cycles}\n"
            f"Max QA Cycles: {cfg.orchestration.max_qa_cycles}\n"
            f"Auto Merge: {cfg.orchestration.auto_merge}\n"
            f"Sequential Issues: {cfg.orchestration.sequential_issues}",
            title="Orchestration",
        )
    )

    # Agents
    agents_table = Table(title="Agents")
    agents_table.add_column("Name", style="cyan")
    agents_table.add_column("Model", style="green")
    agents_table.add_column("Provider", style="magenta")
    agents_table.add_column("Temp", style="yellow")

    for agent_name, agent in cfg.agents.agents.items():
        agents_table.add_row(agent_name, agent.model, agent.provider, str(agent.temperature))

    rprint(agents_table)

    # Providers
    providers_table = Table(title="Providers")
    providers_table.add_column("Name", style="cyan")
    providers_table.add_column("Type", style="green")
    providers_table.add_column("Model", style="magenta")

    for provider_name, provider in cfg.providers.providers.items():
        providers_table.add_row(provider_name, provider.type, provider.default_model)

    rprint(providers_table)


def main() -> None:
    """Main entry point."""
    cli()


if __name__ == "__main__":
    main()
