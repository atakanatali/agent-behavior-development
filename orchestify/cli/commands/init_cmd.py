"""orchestify init — Initialize a sprint in the current git repository."""
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

from orchestify.core.sprint import SprintManager, generate_sprint_id
from orchestify.core.global_config import load_global_config, is_installed
from orchestify.cli.ui.formatting import error, success, info, warn, step

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


def _create_default_configs(config_dir: Path, global_config: dict) -> None:
    """Create default project configuration files."""
    config_dir.mkdir(parents=True, exist_ok=True)

    defaults = global_config.get("defaults", {})
    prefs = global_config.get("preferences", {})
    provider = defaults.get("provider", "anthropic")
    model = defaults.get("model", "claude-opus-4-6")

    # orchestify.yaml
    orchestify_yaml = config_dir / "orchestify.yaml"
    if not orchestify_yaml.exists():
        orchestify_yaml.write_text(f"""project:
  name: "{Path.cwd().name}"
  repo: "owner/{Path.cwd().name}"
  main_branch: "main"
  branch_prefix: "feature/"

orchestration:
  max_review_cycles: {prefs.get('max_review_cycles', 3)}
  max_qa_cycles: {prefs.get('max_qa_cycles', 3)}
  auto_merge: {str(prefs.get('auto_merge', False)).lower()}
  sequential_issues: {str(prefs.get('sequential_issues', True)).lower()}

issue:
  max_changes_per_issue: 20
  language: "{defaults.get('language', 'en')}"
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
""")

    # agents.yaml
    agents_yaml = config_dir / "agents.yaml"
    if not agents_yaml.exists():
        agents_yaml.write_text(f"""agents:
  tpm:
    provider: {provider}
    model: {model}
    temperature: 0.7
    thinking: true
    mode: interactive
    max_tokens: 8192
  engineer:
    provider: {provider}
    model: {model}
    temperature: 0.5
    thinking: false
    mode: autonomous
    max_tokens: 8192
  reviewer:
    provider: {provider}
    model: {model}
    temperature: 0.5
    thinking: false
    mode: autonomous
    max_tokens: 4096
  qa:
    provider: {provider}
    model: {model}
    temperature: 0.7
    thinking: false
    mode: autonomous
    max_tokens: 4096
  architect:
    provider: {provider}
    model: {model}
    temperature: 0.6
    thinking: true
    mode: autonomous
    max_tokens: 8192
""")

    # providers.yaml
    providers_yaml = config_dir / "providers.yaml"
    if not providers_yaml.exists():
        providers_yaml.write_text(f"""providers:
  anthropic:
    type: anthropic
    api_key: ${{ANTHROPIC_API_KEY}}
    default_model: claude-opus-4-6
    max_tokens: 8192
  openai:
    type: openai
    api_key: ${{OPENAI_API_KEY}}
    default_model: gpt-4
    max_tokens: 8192
""")

    # memory.yaml
    memory_yaml = config_dir / "memory.yaml"
    if not memory_yaml.exists():
        mem_config = global_config.get("memory", {})
        memory_yaml.write_text(f"""contextify:
  enabled: {str(mem_config.get('enabled', False)).lower()}
  host: "{mem_config.get('contextify_host', 'http://localhost:8080')}"
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
""")


@click.command()
@click.option("--name", help="Custom sprint name/ID")
@click.option("--prompt", "-p", help="Initial prompt/goal for the sprint")
@click.option("--no-git-check", is_flag=True, help="Skip git repository check")
def init(name: Optional[str], prompt: Optional[str], no_git_check: bool) -> None:
    """Initialize a new sprint in the current git repository.

    Creates the .orchestify/ directory structure and config files.
    Each sprint gets an isolated execution context.
    """
    repo_root = Path.cwd()

    # Check git repo
    if not no_git_check and not _check_git_repo(repo_root):
        error("Not a git repository. Run this command in a git repo.")
        console.print("[dim]Use --no-git-check to skip this check.[/dim]")
        sys.exit(1)

    # Check gh CLI
    if not _check_gh_cli():
        warn("GitHub CLI (gh) not found. Some features may not work.")

    # Load global config
    global_config = load_global_config()

    # Create project config if needed
    config_dir = repo_root / "config"
    if not config_dir.exists():
        step(1, 4, "Creating project configuration...")
        _create_default_configs(config_dir, global_config)
    else:
        step(1, 4, "Project configuration found.")

    # Create sprint
    step(2, 4, "Creating sprint...")
    sprint_manager = SprintManager(repo_root)
    sprint = sprint_manager.create(sprint_id=name, prompt=prompt)

    # Update .gitignore
    step(3, 4, "Updating .gitignore...")
    sprint_manager.update_gitignore()

    # Summary
    step(4, 4, "Done!")

    console.print()
    console.print(Panel(
        f"[bold green]Sprint initialized![/bold green]\n\n"
        f"Sprint ID: [bold cyan]{sprint.sprint_id}[/bold cyan]\n"
        f"Directory: [dim]{sprint.sprint_dir}[/dim]\n"
        + (f"Prompt: [yellow]{prompt}[/yellow]\n" if prompt else "")
        + "\n"
        f"Next steps:\n"
        f"  [cyan]orchestify plan[/cyan]           Plan with TPM agent\n"
        f"  [cyan]orchestify start[/cyan]          Run the pipeline\n"
        f"  [cyan]orchestify status[/cyan]         Check sprint status",
        title=f"Sprint: {sprint.sprint_id}",
        border_style="green",
    ))
