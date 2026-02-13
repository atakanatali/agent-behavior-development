"""
Base Engineer agent for implementation and self-fixing.

Implements core development workflow: branch creation, code generation,
self-fix loop (build/lint/test), commit, and PR creation.
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional

from orchestify.agents.base import ConcreteAgent
from orchestify.core.agent import AgentContext, AgentResult
from orchestify.github import PullRequestManager
from orchestify.github.client import GitHubClient
from orchestify.tools import FileOps, GitOps, DevLoop, DevLoopConfig, ProjectScanner

logger = logging.getLogger(__name__)


class EngineerAgent(ConcreteAgent):
    """
    Base Engineer agent with shared development workflow.

    Implements:
    - Issue-based development (branch per issue)
    - Code generation from specifications
    - Self-fix loop (build, lint, test)
    - Commit and PR creation
    - Review comment handling

    Subclasses override domain attribute and persona loading.
    """

    domain: str = "generic"

    def __init__(self, *args, **kwargs):
        """Initialize engineer agent."""
        super().__init__(*args, **kwargs)
        self._github_client: GitHubClient | None = None
        self._pr_manager: PullRequestManager | None = None
        self._file_ops: FileOps | None = None
        self._git_ops: GitOps | None = None
        self._dev_loop: DevLoop | None = None

    def _get_file_ops(self) -> FileOps:
        """Get or create file operations tool."""
        if not self._file_ops:
            from pathlib import Path

            repo_root = Path(self.config.get("repo_root", "."))
            self._file_ops = FileOps(repo_root)
        return self._file_ops

    def _get_git_ops(self) -> GitOps:
        """Get or create git operations tool."""
        if not self._git_ops:
            from pathlib import Path

            repo_root = Path(self.config.get("repo_root", "."))
            self._git_ops = GitOps(repo_root)
        return self._git_ops

    def _get_dev_loop(self) -> DevLoop:
        """Get or create dev loop tool."""
        if not self._dev_loop:
            from pathlib import Path

            repo_root = Path(self.config.get("repo_root", "."))
            config = DevLoopConfig(
                repo_root=repo_root,
                max_iterations=self.config.get("dev_loop_max_iterations", 5),
            )
            self._dev_loop = DevLoop(config)
        return self._dev_loop

    def _get_pr_manager(self) -> PullRequestManager:
        """Get or create PR manager."""
        if not self._pr_manager:
            if not self._github_client:
                self._github_client = self._init_github_client()
            self._pr_manager = PullRequestManager(self._github_client)
        return self._pr_manager

    def _init_github_client(self) -> GitHubClient:
        """Initialize GitHub client."""
        github_token = self.config.get("github_token")
        if not github_token:
            raise RuntimeError("GitHub token not configured for engineer agent")
        return GitHubClient(
            token=github_token,
            repo_owner=self.config.get("repo_owner"),
            repo_name=self.config.get("repo_name"),
        )

    async def execute(self, context: AgentContext) -> AgentResult:
        """
        Execute engineer agent task.

        Args:
            context: Agent execution context with issue details

        Returns:
            Agent result with PR number
        """
        issue_num = context.memory_context.get("issue_number", 1) if context.memory_context else 1
        issue_dict = {
            "number": issue_num,
            "title": context.goal,
            "body": context.behavior_spec,
        }

        pr_number = await self.execute_development(issue_dict)
        return AgentResult(
            output=f"Created PR #{pr_number}",
            commands_run=["git:branch", "code:generate", "test:run", "git:commit", "pr:create"],
        )

    async def execute_development(self, issue: Dict) -> int:
        """
        Execute full development cycle for an issue.

        Performs:
        1. Create branch from issue
        2. Generate code changes
        3. Apply changes to disk
        4. Run self-fix loop
        5. Commit changes
        6. Create PR

        Args:
            issue: Issue dictionary with number, title, body

        Returns:
            Created PR number

        Raises:
            RuntimeError: If development fails
        """
        start_time = time.time()
        file_ops = self._get_file_ops()
        git_ops = self._get_git_ops()

        try:
            issue_num = issue.get("number", 1)
            branch_name = f"issue-{issue_num}"

            logger.info(f"Starting development for issue #{issue_num}")

            # Step 1: Create branch
            try:
                git_ops.create_branch(branch_name, base="main")
                logger.info(f"Created branch {branch_name}")
            except Exception as e:
                logger.warning(f"Branch creation failed: {e}")

            # Step 2: Generate code changes
            changes = await self._generate_code(issue)
            logger.info(f"Generated {len(changes)} code changes")

            # Step 3: Apply changes
            await self._apply_changes(changes)
            logger.info("Applied code changes")

            # Step 4: Run self-fix loop
            fixed = await self._run_self_fix_loop(issue)
            if not fixed:
                logger.warning("Self-fix loop did not fully resolve issues")

            # Step 5: Commit changes
            try:
                git_ops.add(".")
                commit_msg = f"Implement issue #{issue_num}: {issue.get('title', 'untitled')}"
                commit_hash = git_ops.commit(commit_msg)
                logger.info(f"Committed with hash {commit_hash}")
            except Exception as e:
                logger.warning(f"Commit failed: {e}")
                raise RuntimeError(f"Commit failed: {e}") from e

            # Step 6: Push and create PR
            try:
                git_ops.push(branch=branch_name, set_upstream=True)
                logger.info(f"Pushed branch {branch_name}")
            except Exception as e:
                logger.warning(f"Push failed: {e}")

            # Create PR
            pr_manager = self._get_pr_manager()
            github_client = self._github_client or self._init_github_client()
            repo = github_client.get_repo()

            pr_body = f"""
## Issue
Closes #{issue_num}

## Description
{issue.get('body', 'Implementation of issue')}

## Changes
- {len(changes)} code changes applied

## Self-Fix
- Passed self-fix loop: {fixed}
"""

            try:
                pr = repo.create_pull(
                    title=f"Implement issue #{issue_num}: {issue.get('title', '')}",
                    body=pr_body,
                    head=branch_name,
                    base="main",
                )
                pr_number = pr.number
                logger.info(f"Created PR #{pr_number}")
            except Exception as e:
                logger.error(f"PR creation failed: {e}")
                raise RuntimeError(f"PR creation failed: {e}") from e

            # Log interaction
            result = AgentResult(
                output=f"Completed development for issue #{issue_num}, created PR #{pr_number}",
                files_changed=[c.get("path", "") for c in changes],
                commands_run=[
                    f"git:branch:{branch_name}",
                    f"code:generate:{len(changes)}",
                    "test:self-fix",
                    f"git:commit",
                    f"git:push",
                    f"pr:create:{pr_number}",
                ],
                duration=time.time() - start_time,
            )
            self._log_interaction(
                AgentContext(goal=f"Develop issue #{issue_num}", instructions="", behavior_spec=""),
                result,
            )

            return pr_number

        except Exception as e:
            logger.error(f"Development execution failed: {e}")
            raise RuntimeError(f"Development execution failed: {e}") from e

    async def _generate_code(
        self, issue: Dict, error_context: str = ""
    ) -> List[Dict[str, str]]:
        """
        Generate code changes for issue.

        Returns list of changes with path, content, and action.

        Args:
            issue: Issue dictionary
            error_context: Optional error context for self-fix iterations

        Returns:
            List of change dictionaries with keys: path, content, action (create/modify/delete)
        """
        file_ops = self._get_file_ops()
        project_scanner = ProjectScanner(file_ops.repo_root)

        # Get project context
        project_info = project_scanner.scan()

        code_context = AgentContext(
            goal=f"Generate code changes for issue: {issue.get('title', '')}",
            instructions=f"Issue description:\n{issue.get('body', '')}",
            behavior_spec="Generate code changes as a list of:\n- path: file path\n- content: full file content\n- action: create/modify/delete",
            prior_output=error_context if error_context else None,
            memory_context={
                "domain": self.domain,
                "project_files": len(project_info.files),
                "issue_number": issue.get("number"),
            },
        )

        response = await self._call_llm(code_context)

        # Parse response into changes
        changes = self._parse_code_changes(response)
        logger.debug(f"Parsed {len(changes)} code changes from LLM response")

        return changes

    async def _apply_changes(self, changes: List[Dict[str, str]]) -> None:
        """
        Apply code changes to disk.

        Args:
            changes: List of change dictionaries

        Raises:
            RuntimeError: If applying changes fails
        """
        file_ops = self._get_file_ops()

        for change in changes:
            path = change.get("path", "")
            content = change.get("content", "")
            action = change.get("action", "modify")

            try:
                if action == "create":
                    file_ops.create_file(path, content)
                    logger.info(f"Created file {path}")
                elif action == "modify":
                    file_ops.write_file(path, content)
                    logger.info(f"Modified file {path}")
                elif action == "delete":
                    file_ops.delete_file(path)
                    logger.info(f"Deleted file {path}")
            except Exception as e:
                logger.error(f"Failed to apply change to {path}: {e}")
                raise RuntimeError(f"Failed to apply changes: {e}") from e

    async def _run_self_fix_loop(self, issue: Dict) -> bool:
        """
        Run self-fix loop: build, lint, test with iteration.

        Args:
            issue: Issue dictionary

        Returns:
            True if all checks pass, False otherwise
        """
        dev_loop = self._get_dev_loop()

        try:
            result = await dev_loop.execute()
            logger.info(
                f"Dev loop completed: {result.passed_checks}/{result.total_checks} checks passed"
            )
            return result.passed_checks == result.total_checks
        except Exception as e:
            logger.warning(f"Self-fix loop failed: {e}")
            return False

    async def _handle_review_comments(self, pr_number: int) -> bool:
        """
        Handle review comments and make fixes.

        Args:
            pr_number: PR number

        Returns:
            True if all comments resolved, False otherwise
        """
        github_client = self._github_client or self._init_github_client()
        repo = github_client.get_repo()

        try:
            pr = repo.get_pull(pr_number)
            comments = list(pr.get_comments())

            if not comments:
                logger.info(f"No review comments on PR #{pr_number}")
                return True

            logger.info(f"Found {len(comments)} review comments on PR #{pr_number}")

            for comment in comments:
                # Generate fix for comment
                fix_context = AgentContext(
                    goal=f"Fix review comment on PR #{pr_number}",
                    instructions=f"Review comment:\n{comment.body}",
                    behavior_spec="Generate minimal fix to address the review comment",
                )

                fix_response = await self._call_llm(fix_context)

                # Parse and apply fix
                changes = self._parse_code_changes(fix_response)
                await self._apply_changes(changes)

                logger.info(f"Applied fix for comment {comment.id}")

            # Commit fixes
            git_ops = self._get_git_ops()
            git_ops.add(".")
            git_ops.commit(f"Address review comments on PR #{pr_number}")
            git_ops.push()

            return True

        except Exception as e:
            logger.warning(f"Failed to handle review comments: {e}")
            return False

    def _parse_code_changes(self, response: str) -> List[Dict[str, str]]:
        """
        Parse code changes from LLM response.

        Expected format: path:..., action:..., content:...

        Args:
            response: LLM response text

        Returns:
            List of change dictionaries
        """
        changes = []
        blocks = response.split("---")

        for block in blocks:
            if not block.strip():
                continue

            change = {"path": "", "content": "", "action": "modify"}
            lines = block.split("\n")

            for line in lines:
                if line.startswith("path:"):
                    change["path"] = line.replace("path:", "").strip()
                elif line.startswith("action:"):
                    change["action"] = line.replace("action:", "").strip()
                elif line.startswith("content:"):
                    # Everything after content: is the content
                    idx = block.find("content:")
                    if idx != -1:
                        change["content"] = block[idx + 8 :].strip()
                    break

            if change["path"]:
                changes.append(change)

        return changes
