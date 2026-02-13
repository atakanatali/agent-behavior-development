"""
Shell command execution tool for agents.

Provides safe shell command execution with timeout and output capture.
"""

import logging
import shlex
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ShellResult:
    """Result of a shell command execution."""

    command: str
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: int
    success: bool

    def __repr__(self) -> str:
        """String representation of shell result."""
        return (
            f"ShellResult(command={self.command!r}, exit_code={self.exit_code}, "
            f"duration_ms={self.duration_ms}, success={self.success})"
        )


class ShellRunner:
    """
    Shell command execution tool for agents.

    Provides safe command execution with timeout enforcement,
    output capture, and execution logging.
    """

    def __init__(self, working_dir: Path, timeout: int = 120) -> None:
        """
        Initialize ShellRunner with a working directory.

        Args:
            working_dir: The directory to execute commands in.
            timeout: Default timeout in seconds for commands (default 120).

        Raises:
            ValueError: If working_dir does not exist or is not a directory.
        """
        self.working_dir = working_dir.resolve()
        self.default_timeout = timeout

        if not self.working_dir.exists():
            raise ValueError(f"Working directory does not exist: {self.working_dir}")

        if not self.working_dir.is_dir():
            raise ValueError(
                f"Working directory is not a directory: {self.working_dir}"
            )

        logger.debug(
            f"ShellRunner initialized with working_dir={self.working_dir}, "
            f"default_timeout={timeout}s"
        )

    def run(
        self, command: str, timeout: Optional[int] = None
    ) -> ShellResult:
        """
        Execute a shell command.

        Args:
            command: The command to execute.
            timeout: Timeout in seconds. Uses default_timeout if not specified.

        Returns:
            ShellResult with command output and status.
        """
        timeout = timeout or self.default_timeout

        logger.debug(f"Running command: {command}")

        start_time = time.time()

        try:
            # Use shlex to properly parse the command without shell=True
            # This is more secure than shell=True
            args = shlex.split(command)

            result = subprocess.run(
                args,
                cwd=str(self.working_dir),
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            duration_ms = int((time.time() - start_time) * 1000)

            shell_result = ShellResult(
                command=command,
                exit_code=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                duration_ms=duration_ms,
                success=result.returncode == 0,
            )

            log_level = logging.DEBUG if shell_result.success else logging.WARNING
            logger.log(
                log_level,
                f"Command completed: {command} (exit_code={result.returncode}, "
                f"duration={duration_ms}ms)",
            )

            return shell_result

        except subprocess.TimeoutExpired:
            duration_ms = int((time.time() - start_time) * 1000)

            logger.error(f"Command timed out after {timeout}s: {command}")

            return ShellResult(
                command=command,
                exit_code=-1,
                stdout="",
                stderr=f"Command timed out after {timeout} seconds",
                duration_ms=duration_ms,
                success=False,
            )

        except FileNotFoundError as e:
            duration_ms = int((time.time() - start_time) * 1000)

            logger.error(f"Command not found: {command} - {e}")

            return ShellResult(
                command=command,
                exit_code=-1,
                stdout="",
                stderr=f"Command not found: {str(e)}",
                duration_ms=duration_ms,
                success=False,
            )

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)

            logger.error(f"Unexpected error running command {command}: {e}")

            return ShellResult(
                command=command,
                exit_code=-1,
                stdout="",
                stderr=f"Unexpected error: {str(e)}",
                duration_ms=duration_ms,
                success=False,
            )

    def run_sequence(self, commands: List[str]) -> List[ShellResult]:
        """
        Execute a sequence of commands, stopping on first failure.

        Args:
            commands: List of commands to execute in order.

        Returns:
            List of ShellResult objects, one for each command.
            Stops executing on the first failure.
        """
        results: List[ShellResult] = []

        for command in commands:
            result = self.run(command)
            results.append(result)

            if not result.success:
                logger.info(
                    f"Stopping sequence execution due to failed command: {command}"
                )
                break

        return results
