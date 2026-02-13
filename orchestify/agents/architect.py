"""
Team Lead Architect agent for design review and issue distribution.

Reviews issues against architecture, enriches with technical details,
distributes to specialized engineers, and performs final PR review.
"""

import logging
import time
from typing import Dict, List

from orchestify.agents.base import ConcreteAgent
from orchestify.core.agent import AgentContext, AgentResult
from orchestify.github import IssueManager, PullRequestManager
from orchestify.github.client import GitHubClient
from orchestify.tools import FileOps

logger = logging.getLogger(__name__)


class ArchitectAgent(ConcreteAgent):
    """
    Team Lead Architect agent.

    Responsible for:
    - Reviewing issues against architecture guidelines
    - Enriching issues with technical design details
    - Assigning issues to specialized engineer agents
    - Performing final architecture review on PRs
    - Merging approved PRs
    """

    def __init__(self, *args, **kwargs):
        """Initialize architect agent."""
        super().__init__(*args, **kwargs)
        self._github_client: GitHubClient | None = None
        self._issue_manager: IssueManager | None = None
        self._pr_manager: PullRequestManager | None = None
        self._file_ops: FileOps | None = None

    def _get_issue_manager(self) -> IssueManager:
        """Get or create GitHub issue manager."""
        if not self._issue_manager:
            if not self._github_client:
                self._github_client = self._init_github_client()
            self._issue_manager = IssueManager(self._github_client)
        return self._issue_manager

    def _get_pr_manager(self) -> PullRequestManager:
        """Get or create GitHub PR manager."""
        if not self._pr_manager:
            if not self._github_client:
                self._github_client = self._init_github_client()
            self._pr_manager = PullRequestManager(self._github_client)
        return self._pr_manager

    def _get_file_ops(self) -> FileOps:
        """Get or create file operations tool."""
        if not self._file_ops:
            from pathlib import Path

            repo_root = Path(self.config.get("repo_root", "."))
            self._file_ops = FileOps(repo_root)
        return self._file_ops

    def _init_github_client(self) -> GitHubClient:
        """Initialize GitHub client."""
        github_token = self.config.get("github_token")
        if not github_token:
            raise RuntimeError("GitHub token not configured for architect agent")
        return GitHubClient(
            token=github_token,
            repo_owner=self.config.get("repo_owner"),
            repo_name=self.config.get("repo_name"),
        )

    async def execute(self, context: AgentContext) -> AgentResult:
        """
        Execute architect agent task.

        Routes to appropriate method based on context.

        Args:
            context: Agent execution context

        Returns:
            Agent result
        """
        # Default to review
        result = await self.execute_review(
            epic_id=context.memory_context.get("epic_id", 1)
            if context.memory_context
            else 1
        )
        return result

    async def execute_review(self, epic_id: int) -> None:
        """
        Review all issues in epic against architecture.

        Enriches issues with technical design details and validates
        against architecture guidelines.

        Args:
            epic_id: Epic (milestone) ID to review

        Raises:
            RuntimeError: If review fails
        """
        start_time = time.time()

        try:
            issue_manager = self._get_issue_manager()
            file_ops = self._get_file_ops()

            # Load architecture context
            arch_context = self._load_architecture_context(file_ops)

            logger.info(f"Reviewing epic {epic_id} against architecture")

            # Get all issues in milestone
            github_client = self._github_client or self._init_github_client()
            repo = github_client.get_repo()
            milestone = None

            for m in repo.get_milestones():
                if m.number == epic_id:
                    milestone = m
                    break

            if not milestone:
                raise RuntimeError(f"Milestone {epic_id} not found")

            issues = list(milestone.get_issues(state="open"))

            # Review each issue
            for issue in issues:
                review_context = AgentContext(
                    goal=f"Review and enrich issue #{issue.number}",
                    instructions=f"Issue title: {issue.title}\nIssue body: {issue.body}",
                    behavior_spec=arch_context,
                )

                enrichment = await self._call_llm(review_context)

                # Update issue with enrichment
                try:
                    issue_manager.update_issue(
                        issue_number=issue.number,
                        body=f"{issue.body}\n\n## Architecture Review\n{enrichment}",
                    )
                    logger.info(f"Enriched issue #{issue.number}")
                except Exception as e:
                    logger.warning(f"Failed to enrich issue #{issue.number}: {e}")

        except Exception as e:
            logger.error(f"Architecture review failed: {e}")
            raise RuntimeError(f"Architecture review failed: {e}") from e

    async def execute_distribute(self, epic_id: int) -> List[Dict[str, str]]:
        """
        Assign issues to agents based on technical domain.

        Analyzes issue labels and content to determine appropriate
        engineer specialization (frontend/backend/ios/android).

        Args:
            epic_id: Epic (milestone) ID to distribute

        Returns:
            List of assignment dictionaries with issue_number, agent_type, reason

        Raises:
            RuntimeError: If distribution fails
        """
        start_time = time.time()
        assignments = []

        try:
            github_client = self._github_client or self._init_github_client()
            repo = github_client.get_repo()

            # Get milestone
            milestone = None
            for m in repo.get_milestones():
                if m.number == epic_id:
                    milestone = m
                    break

            if not milestone:
                raise RuntimeError(f"Milestone {epic_id} not found")

            # Get all issues
            issues = list(milestone.get_issues(state="open"))

            for issue in issues:
                # Determine domain from labels and content
                domain = self._determine_domain(issue)

                # Add label if not present
                label_map = {
                    "frontend": "frontend",
                    "backend": "backend",
                    "ios": "ios",
                    "android": "android",
                }

                if domain in label_map:
                    try:
                        # Add domain label
                        current_labels = [l.name for l in issue.labels]
                        if label_map[domain] not in current_labels:
                            current_labels.append(label_map[domain])
                            issue.edit(labels=current_labels)
                    except Exception as e:
                        logger.warning(f"Failed to add label to issue: {e}")

                assignment = {
                    "issue_number": str(issue.number),
                    "agent_type": f"{domain}_engineer",
                    "reason": f"Identified as {domain} task based on content analysis",
                }
                assignments.append(assignment)
                logger.info(
                    f"Assigned issue #{issue.number} to {domain} engineer"
                )

            return assignments

        except Exception as e:
            logger.error(f"Issue distribution failed: {e}")
            raise RuntimeError(f"Issue distribution failed: {e}") from e

    async def execute_final_review(
        self, pr_number: int, issue_number: int
    ) -> bool:
        """
        Perform final architecture review on PR.

        Reviews PR against architecture, approves/requests changes,
        and merges if approved.

        Args:
            pr_number: Pull request number
            issue_number: Associated issue number

        Returns:
            True if approved and merged, False otherwise

        Raises:
            RuntimeError: If review fails
        """
        start_time = time.time()

        try:
            pr_manager = self._get_pr_manager()
            file_ops = self._get_file_ops()

            # Load architecture context
            arch_context = self._load_architecture_context(file_ops)

            logger.info(f"Final architecture review of PR #{pr_number}")

            # Get PR details
            github_client = self._github_client or self._init_github_client()
            repo = github_client.get_repo()
            pr = repo.get_pull(pr_number)

            # Get diff
            diff = pr.get_issue_comments()

            # Review context
            review_context = AgentContext(
                goal=f"Perform final architecture review of PR #{pr_number}",
                instructions=f"PR title: {pr.title}\nLinked issue: #{issue_number}",
                behavior_spec=arch_context,
                prior_output=f"PR diff summary: {len(list(pr.get_files()))} files changed",
                memory_context={
                    "pr_number": pr_number,
                    "issue_number": issue_number,
                },
            )

            review_result = await self._call_llm(review_context)

            # Check if approved
            approved = "approved" in review_result.lower() and (
                "merge" in review_result.lower()
            )

            if approved:
                try:
                    pr.merge()
                    logger.info(f"Merged PR #{pr_number}")
                except Exception as e:
                    logger.warning(f"Failed to merge PR: {e}")
                    return False
            else:
                # Post review comment
                try:
                    pr.create_issue_comment(
                        f"Architecture review: {review_result}"
                    )
                    logger.info(f"Posted review comment on PR #{pr_number}")
                except Exception as e:
                    logger.warning(f"Failed to post review comment: {e}")

            return approved

        except Exception as e:
            logger.error(f"Final architecture review failed: {e}")
            raise RuntimeError(
                f"Final architecture review failed: {e}"
            ) from e

    def _load_architecture_context(self, file_ops: FileOps) -> str:
        """
        Load architecture context from project files.

        Args:
            file_ops: FileOps instance

        Returns:
            Architecture context string
        """
        context_parts = []

        # Try to load architecture.md
        try:
            arch_doc = file_ops.read_file("architecture.md")
            context_parts.append(f"Architecture Documentation:\n{arch_doc}")
        except FileNotFoundError:
            logger.debug("architecture.md not found")

        # Try to load project structure
        try:
            project_structure = file_ops.read_file("PROJECT_STRUCTURE.md")
            context_parts.append(f"Project Structure:\n{project_structure}")
        except FileNotFoundError:
            logger.debug("PROJECT_STRUCTURE.md not found")

        # Add default architecture guidelines
        context_parts.append(
            """
Architecture Guidelines:
- Follow SOLID principles
- Maintain clear separation of concerns
- Use dependency injection where appropriate
- Ensure backward compatibility
- Document breaking changes
- Test all public APIs
- Keep components focused and reusable
"""
        )

        return "\n\n".join(context_parts)

    def _determine_domain(self, issue) -> str:
        """
        Determine technical domain from issue labels and content.

        Args:
            issue: GitHub issue object

        Returns:
            Domain string: frontend, backend, ios, android
        """
        labels = [label.name.lower() for label in issue.labels]
        content = f"{issue.title} {issue.body}".lower()

        # Check labels first
        for domain in ["frontend", "backend", "ios", "android"]:
            if domain in labels:
                return domain

        # Check content
        frontend_keywords = ["react", "vue", "angular", "css", "html", "ui", "component"]
        backend_keywords = ["api", "database", "server", "endpoint", "auth", "middleware"]
        ios_keywords = ["swift", "ios", "xcode", "swiftui", "uikit"]
        android_keywords = ["kotlin", "android", "gradle", "jetpack", "compose"]

        content_score = {
            "frontend": sum(1 for k in frontend_keywords if k in content),
            "backend": sum(1 for k in backend_keywords if k in content),
            "ios": sum(1 for k in ios_keywords if k in content),
            "android": sum(1 for k in android_keywords if k in content),
        }

        # Return domain with highest score, default to backend
        best_domain = max(content_score, key=content_score.get)
        return best_domain if content_score[best_domain] > 0 else "backend"
