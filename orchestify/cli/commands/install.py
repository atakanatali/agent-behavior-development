"""orchestify install — Global setup wizard."""
import os
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm

from orchestify.core.global_config import (
    DEFAULT_GLOBAL_CONFIG,
    get_global_config_dir,
    load_global_config,
    save_global_config,
    is_installed,
)
from orchestify.cli.ui.formatting import error, success, info, step

console = Console()


@click.command()
@click.option("--force", is_flag=True, help="Overwrite existing configuration")
def install(force: bool) -> None:
    """Run the orchestify install wizard to configure global settings."""
    if is_installed() and not force:
        console.print(
            "[yellow]Orchestify is already installed.[/yellow]\n"
            "Run [cyan]orchestify install --force[/cyan] to reconfigure."
        )
        return

    console.print(Panel(
        "[bold cyan]Orchestify Install Wizard[/bold cyan]\n\n"
        "This will configure your global settings at:\n"
        f"[dim]{get_global_config_dir()}[/dim]",
        border_style="cyan",
    ))

    config = DEFAULT_GLOBAL_CONFIG.copy()

    # Step 1: User info
    step(1, 5, "User Information")
    config["user"]["name"] = Prompt.ask(
        "  Your name",
        default=os.environ.get("USER", ""),
    )
    config["user"]["email"] = Prompt.ask(
        "  Your email",
        default="",
    )

    # Step 2: Default provider
    step(2, 5, "Default LLM Provider")
    provider = Prompt.ask(
        "  Default provider",
        choices=["anthropic", "openai", "litellm"],
        default="anthropic",
    )
    config["defaults"]["provider"] = provider

    # Step 3: API Keys
    step(3, 5, "API Keys")
    console.print("  [dim]Leave empty to use environment variables.[/dim]")

    if provider == "anthropic" or Confirm.ask("  Configure Anthropic API key?", default=False):
        existing = os.environ.get("ANTHROPIC_API_KEY", "")
        if existing:
            console.print("  [green]ANTHROPIC_API_KEY found in environment.[/green]")
        else:
            key = Prompt.ask("  Anthropic API key", password=True, default="")
            if key:
                config["api_keys"]["anthropic"] = key

    if provider == "openai" or Confirm.ask("  Configure OpenAI API key?", default=False):
        existing = os.environ.get("OPENAI_API_KEY", "")
        if existing:
            console.print("  [green]OPENAI_API_KEY found in environment.[/green]")
        else:
            key = Prompt.ask("  OpenAI API key", password=True, default="")
            if key:
                config["api_keys"]["openai"] = key

    # Step 4: Preferences
    step(4, 5, "Preferences")
    config["preferences"]["language"] = Prompt.ask(
        "  Default language",
        choices=["en", "tr"],
        default="en",
    )
    config["preferences"]["auto_merge"] = Confirm.ask(
        "  Auto-merge approved PRs?",
        default=False,
    )

    # Step 5: Memory
    step(5, 5, "Memory (Contextify)")
    config["memory"]["enabled"] = Confirm.ask(
        "  Enable Contextify memory?",
        default=False,
    )
    if config["memory"]["enabled"]:
        config["memory"]["contextify_host"] = Prompt.ask(
            "  Contextify host",
            default="http://localhost:8080",
        )

    # Save config
    config_path = save_global_config(config)
    console.print()
    success(f"Global configuration saved to {config_path}")

    console.print(Panel(
        "[bold green]Installation complete![/bold green]\n\n"
        "Next steps:\n"
        "  1. Navigate to your git repository\n"
        "  2. Run [cyan]orchestify init[/cyan] to create a sprint\n"
        "  3. Run [cyan]orchestify plan[/cyan] to start planning",
        border_style="green",
    ))
