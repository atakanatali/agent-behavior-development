"""
Structured logging module with Rich formatting.

Provides centralized logging for ABD orchestration engine.
"""

import logging
import sys
from pathlib import Path
from typing import Optional

try:
    from rich.logging import RichHandler
    HAS_RICH = True
except ImportError:
    HAS_RICH = False


# Global logger cache
_loggers: dict[str, logging.Logger] = {}


def get_logger(name: str) -> logging.Logger:
    """
    Get or create a logger with consistent formatting.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured logger instance
    """
    if name in _loggers:
        return _loggers[name]

    logger = logging.getLogger(name)

    # Only configure if not already configured
    if not logger.handlers:
        logger.setLevel(logging.DEBUG)

        # Create logs directory
        logs_dir = Path(".orchestify/logs")
        logs_dir.mkdir(parents=True, exist_ok=True)

        # File handler
        file_handler = logging.FileHandler(
            logs_dir / "orchestify.log"
        )
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            fmt="[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

        # Console handler
        if HAS_RICH:
            console_handler = RichHandler(
                rich_tracebacks=True,
                show_time=True,
                show_path=False,
            )
        else:
            console_handler = logging.StreamHandler(sys.stdout)
            console_formatter = logging.Formatter(
                fmt="[%(asctime)s] [%(name)s] %(message)s",
                datefmt="%H:%M:%S",
            )
            console_handler.setFormatter(console_formatter)

        console_handler.setLevel(logging.INFO)
        logger.addHandler(console_handler)

    _loggers[name] = logger
    return logger


def get_file_logger(
    name: str,
    log_file: Optional[Path] = None,
) -> logging.Logger:
    """
    Get a logger that writes to a specific file.

    Args:
        name: Logger name
        log_file: Path to log file (default: .orchestify/logs/{name}.log)

    Returns:
        Configured logger
    """
    logger = logging.getLogger(f"{name}.file")

    if not logger.handlers:
        if log_file is None:
            log_file = Path(f".orchestify/logs/{name}.log")

        log_file.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            fmt="[%(asctime)s] [%(levelname)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    return logger
