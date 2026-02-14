"""orchestify memory — Manage Contextify memory integration."""
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from orchestify.core.global_config import load_global_config
from orchestify.core.sprint import SprintManager
from orchestify.cli.ui.formatting import error, success, warn, info

console = Console()


@click.group()
def memory() -> None:
    """Manage Contextify memory layers and integration."""
    pass


@memory.command()
def status() -> None:
    """Show memory backend status."""
    config = load_global_config()
    mem = config.get("memory", {})

    enabled = mem.get("enabled", False)
    backend = mem.get("backend", "local")
    host = mem.get("contextify_host", "")

    lines = [
        f"Enabled: [{'green' if enabled else 'red'}]{enabled}[/{'green' if enabled else 'red'}]",
        f"Backend: {backend}",
    ]

    if backend == "contextify" or host:
        lines.append(f"Host: {host}")

        # Check connectivity
        try:
            import httpx
            resp = httpx.get(f"{host}/health", timeout=3)
            if resp.status_code == 200:
                lines.append("[green]Connection: OK[/green]")
            else:
                lines.append(f"[red]Connection: HTTP {resp.status_code}[/red]")
        except Exception as e:
            lines.append(f"[red]Connection: Failed ({e})[/red]")

    console.print(Panel(
        "\n".join(lines),
        title="Memory Status",
        border_style="cyan",
    ))


@memory.command()
@click.option("--host", default="http://localhost:8080", help="Contextify host URL")
def start(host: str) -> None:
    """Enable and connect to Contextify memory."""
    config = load_global_config()
    config["memory"]["enabled"] = True
    config["memory"]["backend"] = "contextify"
    config["memory"]["contextify_host"] = host

    from orchestify.core.global_config import save_global_config
    save_global_config(config)

    success(f"Memory enabled. Backend: contextify at {host}")
    console.print("[dim]Memory will be used for all agent interactions.[/dim]")


@memory.command()
def stop() -> None:
    """Disable memory integration."""
    config = load_global_config()
    config["memory"]["enabled"] = False

    from orchestify.core.global_config import save_global_config
    save_global_config(config)

    success("Memory disabled.")


@memory.command()
@click.option("--sprint", "-s", help="Sprint ID (default: latest)")
@click.option("--agent", "-a", help="Filter by agent ID")
@click.option("--layer", type=click.Choice(["agent", "epic", "global"]),
              help="Memory layer to query")
@click.option("--limit", "-n", default=10, help="Number of entries")
def query(
    sprint: Optional[str],
    agent: Optional[str],
    layer: Optional[str],
    limit: int,
) -> None:
    """Query stored memory entries."""
    config = load_global_config()
    mem = config.get("memory", {})

    if not mem.get("enabled", False):
        warn("Memory is not enabled. Run [cyan]orchestify memory start[/cyan] first.")
        return

    # Local fallback
    repo_root = Path.cwd()
    local_memory_dir = repo_root / ".orchestify" / "memory"

    if local_memory_dir.exists():
        import json
        entries = []
        for f in sorted(local_memory_dir.glob("*.json")):
            try:
                data = json.loads(f.read_text())
                if agent and data.get("agent_id") != agent:
                    continue
                if layer and data.get("layer") != layer:
                    continue
                entries.append(data)
            except Exception:
                continue

        if not entries:
            console.print("[dim]No memory entries found.[/dim]")
            return

        table = Table(title="Memory Entries", border_style="cyan")
        table.add_column("Layer", style="cyan")
        table.add_column("Agent", style="green")
        table.add_column("Key", style="white")
        table.add_column("Updated", style="dim")

        for entry in entries[-limit:]:
            table.add_row(
                entry.get("layer", "—"),
                entry.get("agent_id", "—"),
                entry.get("key", "—"),
                entry.get("updated_at", "—")[:19],
            )

        console.print(table)
    else:
        console.print("[dim]No local memory data found.[/dim]")


@memory.command()
@click.confirmation_option(prompt="Are you sure you want to clear all memory?")
def clear() -> None:
    """Clear all memory entries."""
    repo_root = Path.cwd()
    local_memory_dir = repo_root / ".orchestify" / "memory"

    if local_memory_dir.exists():
        import shutil
        shutil.rmtree(local_memory_dir)
        local_memory_dir.mkdir(parents=True, exist_ok=True)
        success("Memory cleared.")
    else:
        console.print("[dim]No memory data to clear.[/dim]")
