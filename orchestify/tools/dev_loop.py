"""
Engineer self-fix development loop tool for agents.

Implements the Claude Code CLI experience for automated development loops.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from orchestify.tools.file_ops import FileOps
from orchestify.tools.git_ops import GitOps
from orchestify.tools.shell import ShellResult, ShellRunner

logger = logging.getLogger(__name__)


@dataclass
class DevLoopConfig:
    """Configuration for the development loop."""

    build_cmd: Optional[str] = None
    lint_cmd: Optional[str] = None
    test_cmd: Optional[str] = None
    max_self_fix: int = 5
    timeout_per_command: int = 120


@dataclass
class SelfFixAttempt:
    """Record of a single self-fix attempt."""

    attempt_number: int
    error_type: str  # "build", "lint", or "test"
    error_message: str
    fix_description: str
    files_modified: List[str]
    result: str  # "pass" or "fail"
    timestamp: str


@dataclass
class DevLoopResult:
    """Result of running all checks in the development loop."""

    build_result: Optional[ShellResult] = None
    lint_result: Optional[ShellResult] = None
    test_result: Optional[ShellResult] = None
    all_passed: bool = False
    first_failure: Optional[str] = None  # "build", "lint", "test", or None
    error_summary: str = ""


class DevLoop:
    """
    Engineer self-fix development loop.

    Implements the Claude Code CLI experience, running build → lint → test
    checks and providing detailed error context for LLM-based fixes.
    """

    def __init__(
        self,
        shell: ShellRunner,
        file_ops: FileOps,
        git_ops: GitOps,
        config: DevLoopConfig,
    ) -> None:
        """
        Initialize the development loop.

        Args:
            shell: ShellRunner for executing commands.
            file_ops: FileOps for file operations.
            git_ops: GitOps for git operations.
            config: DevLoopConfig with command configuration.
        """
        self.shell = shell
        self.file_ops = file_ops
        self.git_ops = git_ops
        self.config = config

        self._attempt_history: List[SelfFixAttempt] = []

        logger.debug(
            f"DevLoop initialized with config: "
            f"build_cmd={config.build_cmd}, lint_cmd={config.lint_cmd}, "
            f"test_cmd={config.test_cmd}, max_self_fix={config.max_self_fix}"
        )

    async def run_checks(self) -> DevLoopResult:
        """
        Run all configured checks in sequence.

        Runs build → lint → test checks, stopping at the first failure.

        Returns:
            DevLoopResult with all check results and status.
        """
        result = DevLoopResult()

        # Run build check
        if self.config.build_cmd:
            logger.info(f"Running build check: {self.config.build_cmd}")
            result.build_result = self.shell.run(
                self.config.build_cmd, timeout=self.config.timeout_per_command
            )

            if not result.build_result.success:
                result.first_failure = "build"
                result.error_summary = self._extract_error_summary(
                    result.build_result
                )
                logger.warning(f"Build check failed")
                return result

        # Run lint check
        if self.config.lint_cmd:
            logger.info(f"Running lint check: {self.config.lint_cmd}")
            result.lint_result = self.shell.run(
                self.config.lint_cmd, timeout=self.config.timeout_per_command
            )

            if not result.lint_result.success:
                result.first_failure = "lint"
                result.error_summary = self._extract_error_summary(
                    result.lint_result
                )
                logger.warning(f"Lint check failed")
                return result

        # Run test check
        if self.config.test_cmd:
            logger.info(f"Running test check: {self.config.test_cmd}")
            result.test_result = self.shell.run(
                self.config.test_cmd, timeout=self.config.timeout_per_command
            )

            if not result.test_result.success:
                result.first_failure = "test"
                result.error_summary = self._extract_error_summary(
                    result.test_result
                )
                logger.warning(f"Test check failed")
                return result

        # All checks passed
        result.all_passed = True
        result.error_summary = "All checks passed"
        logger.info("All checks passed")

        return result

    def get_error_context(self, result: DevLoopResult) -> str:
        """
        Extract and format error information for LLM context.

        Args:
            result: The DevLoopResult to extract error context from.

        Returns:
            Formatted error context string suitable for LLM analysis.
        """
        if result.all_passed:
            return "All checks passed. No errors to report."

        lines = []

        if result.first_failure:
            lines.append(f"First failure: {result.first_failure.upper()}")
            lines.append("")

        # Include the relevant failure result
        if result.first_failure == "build" and result.build_result:
            lines.append("BUILD OUTPUT:")
            lines.append(f"Command: {result.build_result.command}")
            lines.append(f"Exit code: {result.build_result.exit_code}")
            lines.append("")
            if result.build_result.stdout:
                lines.append("STDOUT:")
                lines.append(result.build_result.stdout[-2000:])  # Last 2000 chars
                lines.append("")
            if result.build_result.stderr:
                lines.append("STDERR:")
                lines.append(result.build_result.stderr[-2000:])  # Last 2000 chars
                lines.append("")

        elif result.first_failure == "lint" and result.lint_result:
            lines.append("LINT OUTPUT:")
            lines.append(f"Command: {result.lint_result.command}")
            lines.append(f"Exit code: {result.lint_result.exit_code}")
            lines.append("")
            if result.lint_result.stdout:
                lines.append("STDOUT:")
                lines.append(result.lint_result.stdout[-2000:])  # Last 2000 chars
                lines.append("")
            if result.lint_result.stderr:
                lines.append("STDERR:")
                lines.append(result.lint_result.stderr[-2000:])  # Last 2000 chars
                lines.append("")

        elif result.first_failure == "test" and result.test_result:
            lines.append("TEST OUTPUT:")
            lines.append(f"Command: {result.test_result.command}")
            lines.append(f"Exit code: {result.test_result.exit_code}")
            lines.append("")
            if result.test_result.stdout:
                lines.append("STDOUT:")
                lines.append(result.test_result.stdout[-2000:])  # Last 2000 chars
                lines.append("")
            if result.test_result.stderr:
                lines.append("STDERR:")
                lines.append(result.test_result.stderr[-2000:])  # Last 2000 chars
                lines.append("")

        # Include attempt history
        if self._attempt_history:
            lines.append("PREVIOUS ATTEMPTS:")
            for attempt in self._attempt_history[-3:]:  # Last 3 attempts
                lines.append(f"  Attempt {attempt.attempt_number}: {attempt.result}")
                lines.append(f"    Type: {attempt.error_type}")
                lines.append(f"    Fix: {attempt.fix_description}")
                lines.append("")

        return "\n".join(lines)

    def record_attempt(self, attempt: SelfFixAttempt) -> None:
        """
        Record a self-fix attempt.

        Args:
            attempt: The SelfFixAttempt to record.
        """
        self._attempt_history.append(attempt)
        logger.info(
            f"Recorded attempt #{attempt.attempt_number}: "
            f"{attempt.error_type} -> {attempt.result}"
        )

    def can_retry(self) -> bool:
        """
        Check if more retry attempts are available.

        Returns:
            True if under the max_self_fix limit, False otherwise.
        """
        can_continue = len(self._attempt_history) < self.config.max_self_fix
        logger.debug(
            f"can_retry: {can_continue} "
            f"({len(self._attempt_history)}/{self.config.max_self_fix})"
        )
        return can_continue

    def get_attempt_count(self) -> int:
        """
        Get the current number of attempts.

        Returns:
            The number of attempts made so far.
        """
        return len(self._attempt_history)

    def get_attempt_history(self) -> List[SelfFixAttempt]:
        """
        Get the history of all attempts.

        Returns:
            List of SelfFixAttempt objects.
        """
        return self._attempt_history.copy()

    def generate_escalation_report(self) -> str:
        """
        Generate a report when max attempts exceeded.

        Returns:
            A formatted escalation report string.
        """
        lines = [
            f"ESCALATION REPORT: Max self-fix attempts ({self.config.max_self_fix}) exceeded",
            "",
            "ATTEMPT HISTORY:",
        ]

        for attempt in self._attempt_history:
            lines.append(f"")
            lines.append(f"Attempt {attempt.attempt_number}:")
            lines.append(f"  Type: {attempt.error_type}")
            lines.append(f"  Result: {attempt.result}")
            lines.append(f"  Timestamp: {attempt.timestamp}")
            lines.append(f"  Fix description: {attempt.fix_description}")
            if attempt.files_modified:
                lines.append(f"  Files modified: {', '.join(attempt.files_modified)}")
            lines.append(f"  Error message (first 500 chars):")
            error_excerpt = attempt.error_message[:500]
            for error_line in error_excerpt.split("\n"):
                lines.append(f"    {error_line}")

        lines.append("")
        lines.append("RECOMMENDATION: Manual intervention required")

        return "\n".join(lines)

    def reset(self) -> None:
        """Reset the development loop for a new issue."""
        self._attempt_history.clear()
        logger.info("DevLoop reset")

    def _extract_error_summary(self, result: ShellResult) -> str:
        """
        Extract a brief error summary from a shell result.

        Args:
            result: The ShellResult to extract from.

        Returns:
            A brief error summary string.
        """
        if not result.success:
            # Try to get the first line of stderr or stdout
            error_text = result.stderr or result.stdout
            lines = error_text.split("\n")
            # Find the first non-empty line
            for line in lines:
                if line.strip():
                    return line[:200]  # First 200 chars

        return "Unknown error"
