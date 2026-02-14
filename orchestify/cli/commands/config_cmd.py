"""orchestify config — Configuration management commands."""
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from orchestify.core.config import load_config, validate_config
from orchestify.core.global_config import load_global_config, get_global_config_path
from orchestify.cli.ui.formatting import error, success, warn

console = Console()


@click.group()
def config() -> None:
    """Configuration management commands."""
    pass


@config.command()
def validate() -> None:
    """Validate project configuration files."""
    config_dir = Path.cwd() / "config"

    if not config_dir.exists():
        error("Config directory not found. Run [cyan]orchestify init[/cyan] first.")
        sys.exit(1)

    try:
        cfg = load_config(config_dir)
    except Exception as e:
        console.print(f"[red]Configuration invalid:[/red] {str(e)}")
        sys.exit(1)

    success("Configuration is valid")

    warnings = validate_config(cfg)
    if warnings:
        console.print("\n[yellow]Warnings:[/yellow]")
        for w in warnings:
            console.print(f"  [yellow]![/yellow] {w}")
    else:
        console.print("[green]No warnings found.[/green]")


@config.command()
@click.option("--global", "show_global", is_flag=True, help="Show global config")
def show(show_global: bool) -> None:
    """Display current configuration."""
    if show_global:
        _show_global_config()
        return

    config_dir = Path.cwd() / "config"
    if not config_dir.exists():
        error("Config directory not found. Run [cyan]orchestify init[/cyan] first.")
        sys.exit(1)

    try:
        cfg = load_config(config_dir)
    except Exception as e:
        error(f"Failed to load config: {e}")
        sys.exit(1)

    # Project info
    console.print(Panel(
        f"Name: {cfg.project.name}\nRepo: {cfg.project.repo}\n"
        f"Main Branch: {cfg.project.main_branch}\nBranch Prefix: {cfg.project.branch_prefix}",
        title="Project",
        border_style="cyan",
    ))

    # Orchestration
    console.print(Panel(
        f"Max Review Cycles: {cfg.orchestration.max_review_cycles}\n"
        f"Max QA Cycles: {cfg.orchestration.max_qa_cycles}\n"
        f"Auto Merge: {cfg.orchestration.auto_merge}\n"
        f"Sequential Issues: {cfg.orchestration.sequential_issues}",
        title="Orchestration",
        border_style="cyan",
    ))

    # Agents
    agents_table = Table(title="Agents", border_style="cyan")
    agents_table.add_column("Name", style="cyan")
    agents_table.add_column("Model", style="green")
    agents_table.add_column("Provider", style="magenta")
    agents_table.add_column("Temp", style="yellow")

    for name, agent in cfg.agents.agents.items():
        agents_table.add_row(name, agent.model, agent.provider, str(agent.temperature))

    console.print(agents_table)

    # Providers
    providers_table = Table(title="Providers", border_style="cyan")
    providers_table.add_column("Name", style="cyan")
    providers_table.add_column("Type", style="green")
    providers_table.add_column("Model", style="magenta")

    for name, provider in cfg.providers.providers.items():
        providers_table.add_row(name, provider.type, provider.default_model)

    console.print(providers_table)


def _show_global_config():
    """Show global configuration."""
    config = load_global_config()
    config_path = get_global_config_path()

    lines = [
        f"[dim]Path: {config_path}[/dim]",
        "",
        f"User: {config.get('user', {}).get('name', 'Not set')}",
        f"Email: {config.get('user', {}).get('email', 'Not set')}",
        f"Provider: {config.get('defaults', {}).get('provider', 'anthropic')}",
        f"Model: {config.get('defaults', {}).get('model', 'claude-opus-4-6')}",
        f"Language: {config.get('defaults', {}).get('language', 'en')}",
        "",
        f"Memory: {'Enabled' if config.get('memory', {}).get('enabled') else 'Disabled'}",
    ]

    console.print(Panel(
        "\n".join(lines),
        title="Global Configuration",
        border_style="cyan",
    ))
