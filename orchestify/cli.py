"""Backward compatibility shim — delegates to orchestify.cli.main."""
from orchestify.cli.main import cli, main

__all__ = ["cli", "main"]
