"""orchestify init — Initialize global home and create a sprint (agent session)."""
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel

from orchestify.core.sprint import SprintManager, generate_sprint_id
from orchestify.core.global_config import (
    load_global_config, is_installed,
    get_orchestify_home, ensure_global_home,
)
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


def _init_global_home() -> Path:
    """Initialize the global ~/.orchestify/ home directory."""
    home = ensure_global_home()
    info(f"  Global home: {home}")
    return home


def _init_database():
    """Initialize the SQLite database and run pending migrations."""
    try:
        from orchestify.db.database import DatabaseManager, get_db_path
        from orchestify.migrations.runner import MigrationRunner

        db_path = get_db_path()
        db_path.parent.mkdir(parents=True, exist_ok=True)

        db = DatabaseManager(db_path)
        runner = MigrationRunner(db)

        applied = runner.run_pending()
        if applied:
            for version, desc in applied:
                info(f"  Migration {version:03d}: {desc}")
        else:
            info("  Database is up to date.")

        return db
    except Exception as e:
        warn(f"Database initialization failed: {e}")
        return None


def _create_default_configs(config_dir: Path, global_config: dict) -> None:
    """Create default project configuration files in the git repo's config/ dir."""
    config_dir.mkdir(parents=True, exist_ok=True)

    defaults = global_config.get("defaults", {})
    prefs = global_config.get("preferences", {})
    provider = defaults.get("provider", "anthropic")
    model = defaults.get("model", "claude-opus-4-6")

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


@click.command()
@click.option("--name", help="Custom sprint name/ID")
@click.option("--prompt", "-p", help="Initial prompt/goal for the sprint")
@click.option("--no-git-check", is_flag=True, help="Skip git repository check")
def init(name: Optional[str], prompt: Optional[str], no_git_check: bool) -> None:
    """Initialize orchestify global home and create a new sprint.

    Sets up ~/.orchestify/ (global home with DB, config, personas, etc.)
    and creates a sprint (agent session) in the database.
    """
    repo_root = Path.cwd()

    if not no_git_check and not _check_git_repo(repo_root):
        error("Not a git repository. Run this command in a git repo.")
        console.print("[dim]Use --no-git-check to skip this check.[/dim]")
        sys.exit(1)

    if not _check_gh_cli():
        warn("GitHub CLI (gh) not found. Some features may not work.")

    # Step 1: Global home
    step(1, 4, "Setting up global home (~/.orchestify/)...")
    orchestify_home = _init_global_home()

    # Step 2: Project config
    global_config = load_global_config()
    config_dir = repo_root / "config"
    if not config_dir.exists():
        step(2, 4, "Creating project configuration...")
        _create_default_configs(config_dir, global_config)
    else:
        step(2, 4, "Project configuration found.")

    # Step 3: Database
    step(3, 4, "Initializing database...")
    db = _init_database()
    if db is None:
        error("Database initialization failed. Cannot continue.")
        sys.exit(1)

    # Step 4: Create sprint (DB-only)
    step(4, 4, "Creating sprint...")
    sprint_manager = SprintManager(db)
    sprint = sprint_manager.create(sprint_id=name, prompt=prompt)

    from orchestify.db.database import get_db_path
    db_path = get_db_path()

    console.print()
    console.print(Panel(
        f"[bold green]Sprint initialized![/bold green]\n\n"
        f"Sprint ID:   [bold cyan]{sprint.sprint_id}[/bold cyan]\n"
        f"Global home: [dim]{orchestify_home}[/dim]\n"
        f"Database:    [dim]{db_path}[/dim]\n"
        + (f"Prompt: [yellow]{prompt}[/yellow]\n" if prompt else "")
        + "\n"
        f"Next steps:\n"
        f"  [cyan]orchestify plan[/cyan]           Plan with TPM agent\n"
        f"  [cyan]orchestify start[/cyan]          Run the pipeline\n"
        f"  [cyan]orchestify status[/cyan]         Check sprint status",
        title=f"Sprint: {sprint.sprint_id}",
        border_style="green",
    ))
