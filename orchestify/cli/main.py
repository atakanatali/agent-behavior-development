"""Main CLI entry point for orchestify."""
import sys
from typing import Optional

import click

from orchestify import __version__


@click.group(invoke_without_command=True)
@click.version_option(version=__version__, prog_name="orchestify")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.pass_context
def cli(ctx, verbose: bool) -> None:
    """Orchestify — Agent Behavior Development (ABD) Engine.

    Multi-agent orchestration for software development using the
    behavior-over-code paradigm.

    Run without arguments to see the welcome screen.
    """
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose

    if ctx.invoked_subcommand is None:
        from orchestify.cli.ui.welcome import show_welcome
        show_welcome()


# Register commands
from orchestify.cli.commands.install import install
from orchestify.cli.commands.init_cmd import init
from orchestify.cli.commands.plan import plan
from orchestify.cli.commands.start import start
from orchestify.cli.commands.status import status
from orchestify.cli.commands.inspect_cmd import inspect
from orchestify.cli.commands.memory import memory
from orchestify.cli.commands.stop_resume import stop, resume
from orchestify.cli.commands.config_cmd import config

cli.add_command(install)
cli.add_command(init)
cli.add_command(plan)
cli.add_command(start)
cli.add_command(status)
cli.add_command(inspect)
cli.add_command(memory)
cli.add_command(stop)
cli.add_command(resume)
cli.add_command(config)


def main() -> None:
    """Main entry point."""
    cli()


if __name__ == "__main__":
    main()
