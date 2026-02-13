"""
Project structure analyzer for architect context.

Provides deep project analysis for LLM-based architecture understanding.
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger(__name__)


# Language file extensions mapping
LANGUAGE_EXTENSIONS = {
    "python": {".py"},
    "javascript": {".js", ".mjs"},
    "typescript": {".ts", ".tsx"},
    "java": {".java"},
    "c": {".c", ".h"},
    "cpp": {".cpp", ".cc", ".cxx", ".hpp", ".h"},
    "csharp": {".cs"},
    "go": {".go"},
    "rust": {".rs"},
    "ruby": {".rb"},
    "php": {".php"},
    "swift": {".swift"},
    "kotlin": {".kt"},
    "scala": {".scala"},
}

# Reverse mapping: extension -> language
EXT_TO_LANGUAGE = {}
for lang, exts in LANGUAGE_EXTENSIONS.items():
    for ext in exts:
        EXT_TO_LANGUAGE[ext] = lang


@dataclass
class ProjectStructure:
    """Complete project structure information."""

    root: Path
    languages: Dict[str, int] = field(default_factory=dict)  # language -> file count
    frameworks: List[str] = field(default_factory=list)
    package_managers: List[str] = field(default_factory=list)
    entry_points: List[str] = field(default_factory=list)
    config_files: List[str] = field(default_factory=list)
    directory_tree: str = ""
    total_files: int = 0
    total_lines: int = 0


class ProjectScanner:
    """
    Project structure analyzer for architect context.

    Analyzes a project to determine tech stack, structure, and entry points
    for informed agent decision-making.
    """

    def __init__(self, repo_root: Path) -> None:
        """
        Initialize ProjectScanner.

        Args:
            repo_root: The root directory of the project.

        Raises:
            ValueError: If repo_root does not exist.
        """
        self.repo_root = repo_root.resolve()

        if not self.repo_root.exists():
            raise ValueError(f"Repository root does not exist: {self.repo_root}")

        if not self.repo_root.is_dir():
            raise ValueError(f"Repository root is not a directory: {self.repo_root}")

    def scan(self) -> ProjectStructure:
        """
        Perform a complete project scan.

        Returns:
            ProjectStructure with complete project information.
        """
        logger.info(f"Scanning project: {self.repo_root}")

        structure = ProjectStructure(root=self.repo_root)

        # Scan file languages
        structure.languages = self._detect_languages()
        structure.total_files = sum(structure.languages.values())

        # Detect tech stack
        structure.frameworks = self._detect_frameworks()
        structure.package_managers = self._detect_package_managers()

        # Find special files
        structure.entry_points = self._find_entry_points()
        structure.config_files = self._find_config_files()

        # Generate directory tree
        structure.directory_tree = self._generate_tree()

        # Count lines (approximate)
        structure.total_lines = self._count_lines()

        logger.info(
            f"Scan complete: {structure.total_files} files, "
            f"{len(structure.languages)} languages, "
            f"{len(structure.frameworks)} frameworks"
        )

        return structure

    def get_summary(self) -> str:
        """
        Get a markdown-formatted project summary for LLM context.

        Returns:
            Markdown-formatted project summary.
        """
        structure = self.scan()

        lines = [
            "# Project Structure Summary",
            "",
            "## Overview",
            f"- **Root**: {self.repo_root}",
            f"- **Total Files**: {structure.total_files}",
            f"- **Total Lines**: {structure.total_lines:,}",
            "",
        ]

        if structure.languages:
            lines.append("## Languages")
            for lang, count in sorted(
                structure.languages.items(), key=lambda x: x[1], reverse=True
            ):
                lines.append(f"- {lang.capitalize()}: {count} files")
            lines.append("")

        if structure.frameworks:
            lines.append("## Frameworks")
            for framework in structure.frameworks:
                lines.append(f"- {framework}")
            lines.append("")

        if structure.package_managers:
            lines.append("## Package Managers")
            for pm in structure.package_managers:
                lines.append(f"- {pm}")
            lines.append("")

        if structure.entry_points:
            lines.append("## Entry Points")
            for ep in structure.entry_points:
                lines.append(f"- {ep}")
            lines.append("")

        if structure.config_files:
            lines.append("## Configuration Files")
            for cf in structure.config_files:
                lines.append(f"- {cf}")
            lines.append("")

        lines.append("## Directory Tree")
        lines.append("```")
        lines.append(structure.directory_tree)
        lines.append("```")

        return "\n".join(lines)

    def detect_tech_stack(self) -> Dict[str, List[str]]:
        """
        Detect the technology stack.

        Returns:
            Dictionary with keys: languages, frameworks, package_managers.
        """
        return {
            "languages": list(self._detect_languages().keys()),
            "frameworks": self._detect_frameworks(),
            "package_managers": self._detect_package_managers(),
        }

    def get_file_tree(self, max_depth: int = 4) -> str:
        """
        Get the directory file tree.

        Args:
            max_depth: Maximum depth to traverse.

        Returns:
            Tree representation string.
        """
        lines: List[str] = []

        def _walk(path: Path, prefix: str = "", depth: int = 0) -> None:
            if depth > max_depth:
                return

            try:
                entries = sorted(path.iterdir(), key=lambda p: (p.is_file(), p.name))
            except (PermissionError, OSError):
                return

            # Skip common directories
            skip_dirs = {
                ".git",
                ".github",
                "__pycache__",
                "node_modules",
                ".venv",
                "venv",
                "dist",
                "build",
                ".next",
            }

            for i, entry in enumerate(entries):
                if entry.name.startswith(".") and entry.name not in {
                    ".github",
                    ".gitignore",
                }:
                    continue

                if entry.is_dir() and entry.name in skip_dirs:
                    continue

                is_last = i == len(entries) - 1
                connector = "└── " if is_last else "├── "
                lines.append(f"{prefix}{connector}{entry.name}")

                if entry.is_dir() and depth < max_depth:
                    next_prefix = prefix + ("    " if is_last else "│   ")
                    _walk(entry, next_prefix, depth + 1)

        lines.append(self.repo_root.name + "/")
        _walk(self.repo_root)

        return "\n".join(lines)

    def find_config_files(self) -> List[str]:
        """
        Find configuration files in the project.

        Returns:
            List of relative paths to config files.
        """
        return self._find_config_files()

    def find_entry_points(self) -> List[str]:
        """
        Find entry point files in the project.

        Returns:
            List of relative paths to entry point files.
        """
        return self._find_entry_points()

    def _detect_languages(self) -> Dict[str, int]:
        """Detect programming languages used in the project."""
        language_counts: Dict[str, int] = {}

        try:
            for file_path in self.repo_root.rglob("*"):
                if not file_path.is_file():
                    continue

                # Skip hidden files and directories
                if any(part.startswith(".") for part in file_path.parts):
                    continue

                # Skip common non-code directories
                if any(
                    part in {"node_modules", "__pycache__", "venv", ".venv"}
                    for part in file_path.parts
                ):
                    continue

                ext = file_path.suffix.lower()
                if ext in EXT_TO_LANGUAGE:
                    lang = EXT_TO_LANGUAGE[ext]
                    language_counts[lang] = language_counts.get(lang, 0) + 1

        except Exception as e:
            logger.warning(f"Error detecting languages: {e}")

        return language_counts

    def _detect_frameworks(self) -> List[str]:
        """Detect frameworks based on config files and dependencies."""
        frameworks: List[str] = []

        try:
            # Check for JavaScript/Node frameworks
            if (self.repo_root / "package.json").exists():
                content = (self.repo_root / "package.json").read_text()
                if "react" in content.lower():
                    frameworks.append("React")
                if "vue" in content.lower():
                    frameworks.append("Vue")
                if "angular" in content.lower():
                    frameworks.append("Angular")
                if "next" in content.lower():
                    frameworks.append("Next.js")
                if "express" in content.lower():
                    frameworks.append("Express")

            # Check for Python frameworks
            if (self.repo_root / "requirements.txt").exists():
                content = (self.repo_root / "requirements.txt").read_text()
                if "django" in content.lower():
                    frameworks.append("Django")
                if "flask" in content.lower():
                    frameworks.append("Flask")
                if "fastapi" in content.lower():
                    frameworks.append("FastAPI")

            if (self.repo_root / "pyproject.toml").exists():
                content = (self.repo_root / "pyproject.toml").read_text()
                if "django" in content.lower():
                    if "Django" not in frameworks:
                        frameworks.append("Django")
                if "fastapi" in content.lower():
                    if "FastAPI" not in frameworks:
                        frameworks.append("FastAPI")

            # Check for Ruby frameworks
            if (self.repo_root / "Gemfile").exists():
                content = (self.repo_root / "Gemfile").read_text()
                if "rails" in content.lower():
                    frameworks.append("Rails")

        except Exception as e:
            logger.warning(f"Error detecting frameworks: {e}")

        return frameworks

    def _detect_package_managers(self) -> List[str]:
        """Detect package managers used in the project."""
        managers: List[str] = []

        try:
            if (self.repo_root / "package.json").exists():
                managers.append("npm")
                if (self.repo_root / "yarn.lock").exists():
                    managers.append("yarn")
                if (self.repo_root / "pnpm-lock.yaml").exists():
                    managers.append("pnpm")

            if (self.repo_root / "requirements.txt").exists():
                managers.append("pip")
            if (self.repo_root / "pyproject.toml").exists():
                if "pip" not in managers:
                    managers.append("pip")

            if (self.repo_root / "Gemfile").exists():
                managers.append("bundler")

            if (self.repo_root / "Podfile").exists():
                managers.append("cocoapods")

            if (self.repo_root / "build.gradle").exists():
                managers.append("gradle")

            if (self.repo_root / "pom.xml").exists():
                managers.append("maven")

            if (self.repo_root / "go.mod").exists():
                managers.append("go modules")

            if (self.repo_root / "Cargo.toml").exists():
                managers.append("cargo")

        except Exception as e:
            logger.warning(f"Error detecting package managers: {e}")

        return managers

    def _find_config_files(self) -> List[str]:
        """Find configuration files."""
        config_patterns = [
            "package.json",
            "pyproject.toml",
            "setup.py",
            "requirements.txt",
            "Gemfile",
            "Podfile",
            "build.gradle",
            "pom.xml",
            "go.mod",
            "Cargo.toml",
            ".env",
            ".env.example",
            "docker-compose.yml",
            "Dockerfile",
            "tsconfig.json",
            "jest.config.js",
            "eslint.config.js",
            ".eslintrc",
            ".prettierrc",
            "babel.config.js",
            "webpack.config.js",
            "vite.config.js",
            "tailwind.config.js",
        ]

        found_configs = []

        try:
            for pattern in config_patterns:
                for file_path in self.repo_root.glob(f"**/{pattern}"):
                    try:
                        rel_path = file_path.relative_to(self.repo_root)
                        found_configs.append(str(rel_path))
                    except ValueError:
                        pass

        except Exception as e:
            logger.warning(f"Error finding config files: {e}")

        return sorted(list(set(found_configs)))

    def _find_entry_points(self) -> List[str]:
        """Find entry point files."""
        entry_patterns = [
            ("main.py", 0),
            ("__main__.py", 0),
            ("app.py", 0),
            ("index.js", 0),
            ("index.ts", 0),
            ("main.ts", 0),
            ("main.js", 0),
            ("App.jsx", 0),
            ("App.tsx", 0),
            ("server.js", 0),
            ("server.py", 0),
            ("start.js", 0),
            ("cli.py", 0),
        ]

        found_entries = []

        try:
            for pattern, depth in entry_patterns:
                matches = list(self.repo_root.glob(f"**/{pattern}"))
                for file_path in matches:
                    try:
                        rel_path = file_path.relative_to(self.repo_root)
                        found_entries.append(str(rel_path))
                    except ValueError:
                        pass

        except Exception as e:
            logger.warning(f"Error finding entry points: {e}")

        return sorted(list(set(found_entries)))

    def _generate_tree(self) -> str:
        """Generate directory tree."""
        return self.get_file_tree(max_depth=3)

    def _count_lines(self) -> int:
        """Count approximate total lines of code."""
        total_lines = 0

        try:
            for file_path in self.repo_root.rglob("*"):
                if not file_path.is_file():
                    continue

                # Skip hidden files and directories
                if any(part.startswith(".") for part in file_path.parts):
                    continue

                # Skip common non-code directories and large files
                if any(
                    part
                    in {
                        "node_modules",
                        "__pycache__",
                        "venv",
                        ".venv",
                        "dist",
                        "build",
                    }
                    for part in file_path.parts
                ):
                    continue

                # Count lines for source files
                ext = file_path.suffix.lower()
                if ext in EXT_TO_LANGUAGE:
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            total_lines += len(f.readlines())
                    except Exception:
                        pass

        except Exception as e:
            logger.warning(f"Error counting lines: {e}")

        return total_lines
