"""
File operations tool for agents.

Provides secure, scoped file system access constrained to a repository root.
"""

import os
from pathlib import Path
from typing import List


class FileOps:
    """
    File operations tool with security constraints.

    All operations are scoped to a repository root directory to prevent
    directory traversal attacks. Paths are always relative to repo_root.
    """

    def __init__(self, repo_root: Path) -> None:
        """
        Initialize FileOps with a repository root.

        Args:
            repo_root: The root directory for all file operations.
                      All paths must be within this directory.

        Raises:
            ValueError: If repo_root does not exist.
        """
        self.repo_root = repo_root.resolve()

        if not self.repo_root.exists():
            raise ValueError(f"Repository root does not exist: {self.repo_root}")

        if not self.repo_root.is_dir():
            raise ValueError(f"Repository root is not a directory: {self.repo_root}")

    def _validate_path(self, relative_path: str) -> Path:
        """
        Validate and resolve a path to ensure it's within repo_root.

        Prevents directory traversal attacks by ensuring the resolved path
        is within the repository root.

        Args:
            relative_path: Path relative to repo_root.

        Returns:
            The resolved absolute path.

        Raises:
            ValueError: If the path escapes repo_root.
        """
        # Resolve the path relative to repo_root
        target = (self.repo_root / relative_path).resolve()

        # Ensure the target is within repo_root
        try:
            target.relative_to(self.repo_root)
        except ValueError:
            raise ValueError(
                f"Path escapes repository root: {relative_path} "
                f"(resolved to {target}, outside {self.repo_root})"
            )

        return target

    def read_file(self, relative_path: str) -> str:
        """
        Read file contents.

        Args:
            relative_path: Path relative to repo_root.

        Returns:
            The file contents as a string.

        Raises:
            FileNotFoundError: If the file does not exist.
            ValueError: If the path escapes repo_root.
        """
        target = self._validate_path(relative_path)

        if not target.exists():
            raise FileNotFoundError(f"File not found: {relative_path}")

        if not target.is_file():
            raise ValueError(f"Path is not a file: {relative_path}")

        return target.read_text(encoding="utf-8")

    def write_file(self, relative_path: str, content: str) -> None:
        """
        Write content to a file, creating parent directories if needed.

        If the file exists, it will be overwritten. Parent directories are
        created automatically.

        Args:
            relative_path: Path relative to repo_root.
            content: The content to write.

        Raises:
            ValueError: If the path escapes repo_root.
        """
        target = self._validate_path(relative_path)

        # Create parent directories if they don't exist
        target.parent.mkdir(parents=True, exist_ok=True)

        target.write_text(content, encoding="utf-8")

    def create_file(self, relative_path: str, content: str) -> None:
        """
        Create a new file, raising an error if it already exists.

        Parent directories are created automatically.

        Args:
            relative_path: Path relative to repo_root.
            content: The content to write.

        Raises:
            FileExistsError: If the file already exists.
            ValueError: If the path escapes repo_root.
        """
        target = self._validate_path(relative_path)

        if target.exists():
            raise FileExistsError(f"File already exists: {relative_path}")

        # Create parent directories if they don't exist
        target.parent.mkdir(parents=True, exist_ok=True)

        target.write_text(content, encoding="utf-8")

    def delete_file(self, relative_path: str) -> None:
        """
        Delete a file.

        Args:
            relative_path: Path relative to repo_root.

        Raises:
            FileNotFoundError: If the file does not exist.
            ValueError: If the path escapes repo_root or is not a file.
        """
        target = self._validate_path(relative_path)

        if not target.exists():
            raise FileNotFoundError(f"File not found: {relative_path}")

        if not target.is_file():
            raise ValueError(f"Path is not a file: {relative_path}")

        target.unlink()

    def file_exists(self, relative_path: str) -> bool:
        """
        Check if a file exists.

        Args:
            relative_path: Path relative to repo_root.

        Returns:
            True if the file exists, False otherwise.

        Raises:
            ValueError: If the path escapes repo_root.
        """
        target = self._validate_path(relative_path)
        return target.is_file()

    def list_files(
        self, relative_path: str = ".", pattern: str = "*"
    ) -> List[str]:
        """
        List files in a directory matching a pattern.

        Args:
            relative_path: Directory path relative to repo_root.
            pattern: Glob pattern to match (e.g., "*.py", "**/*.js").

        Returns:
            List of relative paths matching the pattern, relative to repo_root.

        Raises:
            ValueError: If the path escapes repo_root or is not a directory.
        """
        target = self._validate_path(relative_path)

        if not target.exists():
            raise ValueError(f"Directory does not exist: {relative_path}")

        if not target.is_dir():
            raise ValueError(f"Path is not a directory: {relative_path}")

        # Use glob to find matching files
        matches = list(target.glob(pattern))

        # Return relative paths from repo_root
        return [str(m.relative_to(self.repo_root)) for m in matches]

    def read_directory_tree(self, relative_path: str = ".", max_depth: int = 3) -> str:
        """
        Generate a tree-like representation of directory structure.

        Args:
            relative_path: Directory path relative to repo_root.
            max_depth: Maximum depth to traverse (default 3).

        Returns:
            A formatted tree string representation of the directory.

        Raises:
            ValueError: If the path escapes repo_root or is not a directory.
        """
        target = self._validate_path(relative_path)

        if not target.exists():
            raise ValueError(f"Directory does not exist: {relative_path}")

        if not target.is_dir():
            raise ValueError(f"Path is not a directory: {relative_path}")

        lines: List[str] = []

        def _walk(
            path: Path, prefix: str = "", depth: int = 0, is_last: bool = True
        ) -> None:
            if depth > max_depth:
                return

            try:
                entries = sorted(path.iterdir(), key=lambda p: (p.is_file(), p.name))
            except (PermissionError, OSError):
                return

            for i, entry in enumerate(entries):
                is_last_entry = i == len(entries) - 1

                # Build the tree characters
                connector = "└── " if is_last_entry else "├── "
                lines.append(f"{prefix}{connector}{entry.name}")

                # Recurse into directories
                if entry.is_dir() and depth < max_depth:
                    next_prefix = prefix + ("    " if is_last_entry else "│   ")
                    _walk(entry, next_prefix, depth + 1, is_last_entry)

        lines.append(target.name + "/")
        _walk(target)

        return "\n".join(lines)
