"""
Base Reviewer agent for code review and quality assessment.

Performs comprehensive code review including diff analysis,
findings documentation, and approval decision.
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Dict, List

from orchestify.agents.base import ConcreteAgent
from orchestify.core.agent import AgentContext, AgentResult, Scorecard
from orchestify.github import PullRequestManager
from orchestify.github.client import GitHubClient

logger = logging.getLogger(__name__)


@dataclass
class ReviewResult:
    """Result of code review."""

    approved: bool
    comments_count: int
    findings: List[Dict[str, str]] = field(default_factory=list)
    scorecard: Scorecard = field(default_factory=lambda: Scorecard(1, 1, 1, 1, 1))


class ReviewerAgent(ConcreteAgent):
    """
    Base Reviewer agent for code review.

    Implements:
    - PR diff analysis
    - Finding identification and documentation
    - Review comment posting
    - Approval decision making

    Subclasses override domain attribute and persona loading.
    """

    domain: str = "generic"

    def __init__(self, *args, **kwargs):
        """Initialize reviewer agent."""
        super().__init__(*args, **kwargs)
        self._github_client: GitHubClient | None = None
        self._pr_manager: PullRequestManager | None = None

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
            raise RuntimeError("GitHub token not configured for reviewer agent")
        return GitHubClient(
            token=github_token,
            repo_owner=self.config.get("repo_owner"),
            repo_name=self.config.get("repo_name"),
        )

    async def execute(self, context: AgentContext) -> AgentResult:
        """
        Execute reviewer agent task.

        Args:
            context: Agent execution context with PR details

        Returns:
            Agent result with review decision
        """
        pr_num = (
            context.memory_context.get("pr_number", 1)
            if context.memory_context
            else 1
        )
        issue_dict = {"number": pr_num, "title": context.goal, "body": context.behavior_spec}

        result = await self.execute_review(pr_num, issue_dict)
        return AgentResult(
            output=f"Review completed: {'APPROVED' if result.approved else 'CHANGES REQUESTED'}"
        )

    async def execute_review(self, pr_number: int, issue: Dict) -> ReviewResult:
        """
        Execute comprehensive code review.

        Performs:
        1. Get PR details and diff
        2. Analyze diff for findings
        3. Post review comments
        4. Make approval decision

        Args:
            pr_number: Pull request number
            issue: Associated issue dictionary

        Returns:
            ReviewResult with approval decision and findings

        Raises:
            RuntimeError: If review fails
        """
        start_time = time.time()

        try:
            github_client = self._github_client or self._init_github_client()
            repo = github_client.get_repo()
            pr = repo.get_pull(pr_number)

            logger.info(f"Starting review of PR #{pr_number}")

            # Get PR diff
            diff_text = ""
            files = list(pr.get_files())
            for file in files:
                if file.patch:
                    diff_text += f"\n--- {file.filename}\n{file.patch}"

            # Analyze diff
            findings = await self._analyze_diff(diff_text)
            logger.info(f"Found {len(findings)} issues in PR #{pr_number}")

            # Post review comments
            await self._post_review(pr_number, findings, len(findings) == 0)

            # Create result
            approved = len(findings) == 0
            result = ReviewResult(
                approved=approved,
                comments_count=len(findings),
                findings=findings,
                scorecard=Scorecard(
                    scope_control=2 if approved else 1,
                    behavior_fidelity=2 if approved else 1,
                    evidence_orientation=2 if approved else 1,
                    actionability=2 if approved else 1,
                    risk_awareness=2 if approved else 1,
                ),
            )

            # Log interaction
            agent_result = AgentResult(
                output=f"Review of PR #{pr_number}: {'APPROVED' if approved else 'CHANGES REQUESTED'}",
                commands_run=[f"review:pr:{pr_number}", f"comment:post:{len(findings)}"],
                duration=time.time() - start_time,
            )
            self._log_interaction(
                AgentContext(
                    goal=f"Review PR #{pr_number}",
                    instructions="",
                    behavior_spec="",
                ),
                agent_result,
            )

            return result

        except Exception as e:
            logger.error(f"Review execution failed: {e}")
            raise RuntimeError(f"Review execution failed: {e}") from e

    async def _analyze_diff(self, diff: str) -> List[Dict[str, str]]:
        """
        Analyze PR diff for code quality issues.

        Args:
            diff: Unified diff format of PR changes

        Returns:
            List of findings with file, line, severity, and message
        """
        analysis_context = AgentContext(
            goal="Analyze PR diff for code quality issues",
            instructions=f"PR Diff:\n{diff}",
            behavior_spec="Identify issues with: code quality, performance, security, testing, documentation.\nFormat each finding as: FILE:LINE - SEVERITY - MESSAGE",
            memory_context={"domain": self.domain},
        )

        response = await self._call_llm(analysis_context)

        # Parse findings from response
        findings = self._parse_findings(response)
        logger.debug(f"Parsed {len(findings)} findings from diff analysis")

        return findings

    async def _post_review(
        self, pr_number: int, findings: List[Dict[str, str]], approved: bool
    ) -> None:
        """
        Post review comments on PR.

        Args:
            pr_number: Pull request number
            findings: List of findings
            approved: Whether PR is approved

        Raises:
            RuntimeError: If posting fails
        """
        try:
            github_client = self._github_client or self._init_github_client()
            repo = github_client.get_repo()
            pr = repo.get_pull(pr_number)

            # Build review comment
            review_body = "## Code Review\n\n"

            if approved:
                review_body += "Approved! No issues found."
            else:
                review_body += f"Found {len(findings)} issues to address:\n\n"
                for finding in findings:
                    review_body += f"- {finding.get('file', 'unknown')}: {finding.get('message', '')}\n"

            # Post comment
            try:
                pr.create_issue_comment(review_body)
                logger.info(f"Posted review comment on PR #{pr_number}")
            except Exception as e:
                logger.warning(f"Failed to post review comment: {e}")

        except Exception as e:
            logger.error(f"Failed to post review: {e}")
            raise RuntimeError(f"Failed to post review: {e}") from e

    def _parse_findings(self, response: str) -> List[Dict[str, str]]:
        """
        Parse findings from LLM response.

        Expected format: FILE:LINE - SEVERITY - MESSAGE

        Args:
            response: LLM response text

        Returns:
            List of finding dictionaries
        """
        findings = []
        lines = response.split("\n")

        for line in lines:
            if " - " in line:
                parts = line.split(" - ")
                if len(parts) >= 3:
                    file_part = parts[0].strip()
                    severity = parts[1].strip()
                    message = " - ".join(parts[2:]).strip()

                    finding = {
                        "file": file_part.split(":")[0] if ":" in file_part else file_part,
                        "line": file_part.split(":")[1] if ":" in file_part else "unknown",
                        "severity": severity,
                        "message": message,
                    }
                    findings.append(finding)

        return findings
