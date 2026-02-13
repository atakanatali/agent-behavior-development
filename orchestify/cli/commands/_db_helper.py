"""Common helper for getting the global DB instance in CLI commands."""
import sys

from rich.console import Console

from orchestify.cli.ui.formatting import error

console = Console()


def get_db():
    """
    Get the global DatabaseManager instance.

    Exits with error if DB is not available (orchestify init not run yet).
    """
    try:
        from orchestify.db.database import DatabaseManager, get_db_path

        db_path = get_db_path()
        if not db_path.exists():
            error("Database not found. Run [cyan]orchestify init[/cyan] first.")
            sys.exit(1)

        return DatabaseManager(db_path)
    except Exception as e:
        error(f"Failed to open database: {e}")
        sys.exit(1)
