"""Unified GitHub client for ABD orchestration engine."""

import os
import json
import subprocess
from typing import Optional
from github import Github, Repository
from github.GithubException import GithubException


class GitHubClient:
    """
    Unified GitHub client that uses PyGithub for API operations
    and gh CLI for auth-heavy operations.

    Attributes:
        repo_full_name: Repository in "owner/repo" format
        _gh_client: Lazy-loaded PyGithub client
        _repo: Cached PyGithub Repository object
    """

    def __init__(self, repo_full_name: str) -> None:
        """
        Initialize GitHub client.

        Args:
            repo_full_name: Repository in "owner/repo" format (e.g., "anthropic/agents")

        Raises:
            ValueError: If repo_full_name is not in "owner/repo" format
        """
        if "/" not in repo_full_name or repo_full_name.count("/") != 1:
            raise ValueError(
                f"Invalid repo format: {repo_full_name}. Expected 'owner/repo'"
            )

        self.repo_full_name = repo_full_name
        self._gh_client: Optional[Github] = None
        self._repo: Optional[Repository.Repository] = None

    def _get_token(self) -> str:
        """
        Get GitHub token from environment or gh CLI.

        Returns:
            GitHub API token

        Raises:
            RuntimeError: If no token is available
        """
        # Try environment variable first
        token = os.getenv("GITHUB_TOKEN")
        if token:
            return token

        # Try gh CLI auth token
        try:
            result = subprocess.run(
                ["gh", "auth", "token"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        raise RuntimeError(
            "No GitHub token found. Set GITHUB_TOKEN env var or authenticate with 'gh auth login'"
        )

    def _ensure_gh_auth(self) -> None:
        """
        Check that gh CLI is authenticated.

        Raises:
            RuntimeError: If gh CLI is not authenticated
        """
        try:
            result = subprocess.run(
                ["gh", "auth", "status"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode != 0:
                raise RuntimeError(
                    "gh CLI is not authenticated. Run 'gh auth login' to authenticate."
                )
        except FileNotFoundError:
            raise RuntimeError(
                "gh CLI is not installed. Install it from https://github.com/cli/cli"
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError("gh auth status check timed out")

    def _run_gh(self, args: list[str]) -> str:
        """
        Run a gh CLI command.

        Args:
            args: Command arguments (e.g., ["issue", "list", "--repo", "owner/repo"])

        Returns:
            Command output as string

        Raises:
            RuntimeError: If command fails
            subprocess.TimeoutExpired: If command times out
        """
        try:
            result = subprocess.run(
                ["gh"] + args,
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                raise RuntimeError(
                    f"gh command failed: {' '.join(args)}\n{result.stderr}"
                )
            return result.stdout.strip()
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"gh command timed out: {' '.join(args)}")
        except FileNotFoundError:
            raise RuntimeError(
                "gh CLI is not installed. Install it from https://github.com/cli/cli"
            )

    def _get_client(self) -> Github:
        """
        Get or create PyGithub client (lazy initialization).

        Returns:
            Authenticated Github client
        """
        if self._gh_client is None:
            token = self._get_token()
            self._gh_client = Github(token)

        return self._gh_client

    def get_repo(self) -> Repository.Repository:
        """
        Get PyGithub Repository object (cached).

        Returns:
            Github Repository object

        Raises:
            GithubException: If repository cannot be accessed
        """
        if self._repo is None:
            client = self._get_client()
            self._repo = client.get_repo(self.repo_full_name)

        return self._repo

    def is_authenticated(self) -> bool:
        """
        Check if GitHub client is authenticated.

        Returns:
            True if authenticated, False otherwise
        """
        try:
            self._get_token()
            return True
        except RuntimeError:
            return False

    def test_connection(self) -> bool:
        """
        Test GitHub API connection.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            client = self._get_client()
            client.get_user().login
            return True
        except (GithubException, RuntimeError):
            return False
