"""
Technical Product Manager (TPM) agent for spec gathering and issue creation.

Analyzes user input, asks clarifying questions interactively, produces
comprehensive specifications, and creates GitHub issues.
"""

import asyncio
import logging
from typing import List

from orchestify.agents.base import ConcreteAgent
from orchestify.core.agent import AgentContext, AgentResult
from orchestify.github import IssueManager
from orchestify.github.client import GitHubClient

logger = logging.getLogger(__name__)


class TPMAgent(ConcreteAgent):
    """
    Technical Product Manager agent.

    Responsible for:
    - Analyzing user input and requirements
    - Asking clarifying questions (interactive mode)
    - Producing comprehensive technical specifications
    - Creating GitHub issues from specifications
    - Following ABD issue template and guidelines
    """

    def __init__(self, *args, **kwargs):
        """Initialize TPM agent."""
        super().__init__(*args, **kwargs)
        self._github_client: GitHubClient | None = None
        self._issue_manager: IssueManager | None = None

    def _get_issue_manager(self) -> IssueManager:
        """
        Get or create GitHub issue manager.

        Returns:
            IssueManager instance

        Raises:
            RuntimeError: If GitHub client is not configured
        """
        if not self._issue_manager:
            if not self._github_client:
                github_token = self.config.get("github_token")
                if not github_token:
                    raise RuntimeError(
                        "GitHub token not configured for TPM agent"
                    )
                self._github_client = GitHubClient(
                    token=github_token,
                    repo_owner=self.config.get("repo_owner"),
                    repo_name=self.config.get("repo_name"),
                )
            self._issue_manager = IssueManager(self._github_client)

        return self._issue_manager

    async def execute(self, context: AgentContext) -> AgentResult:
        """
        Execute TPM agent task.

        Routes to spec gathering or issue creation based on context.

        Args:
            context: Agent execution context

        Returns:
            Agent result with spec or issue numbers
        """
        # Default to spec gathering
        result = await self.execute_spec_gathering(context.goal)
        return result

    async def execute_spec_gathering(self, user_input: str) -> AgentResult:
        """
        Analyze user input and produce comprehensive spec.

        Interactively asks clarifying questions based on input complexity,
        then generates detailed technical specification following ABD format.

        Args:
            user_input: Initial user requirements/input

        Returns:
            Agent result with comprehensive specification

        Raises:
            RuntimeError: If LLM call fails
        """
        import time

        start_time = time.time()

        try:
            # Step 1: Initial analysis to determine complexity
            analysis_context = AgentContext(
                goal="Analyze user input and determine what clarifying questions to ask",
                instructions=f"User input:\n{user_input}\n\nGenerate 3-5 clarifying questions to better understand the requirements.",
                behavior_spec="Focus on: scope, success criteria, constraints, dependencies, and user needs.",
            )

            analysis_response = await self._call_llm(analysis_context)
            logger.debug(f"Initial analysis response received")

            # Step 2: Interactive questions via CLI
            questions = self._extract_questions(analysis_response)
            answers = {}

            for i, question in enumerate(questions[:5], 1):
                # In production, use rich.prompt or click.prompt
                try:
                    answer = input(f"Q{i}: {question}\nA: ")
                    answers[f"q{i}"] = answer
                except EOFError:
                    # Handle non-interactive mode gracefully
                    answers[f"q{i}"] = "(No input provided)"

            # Step 3: Generate comprehensive spec
            spec_context = AgentContext(
                goal="Generate comprehensive technical specification",
                instructions=f"Original user input:\n{user_input}\n\nClarifying Q&A:\n"
                + "\n".join(
                    [
                        f"Q: {q}\nA: {answers.get(f'q{i}', '(No answer)')}"
                        for i, q in enumerate(questions[:5], 1)
                    ]
                ),
                behavior_spec="Produce a 9-section ABD specification:\n1. Analysis\n2. Strategy\n3. Implementation\n4. Testing\n5. Documentation\n6. Code Changes\n7. Risk Assessment\n8. Metrics\n9. Scorecard (JSON)",
                memory_context={
                    "user_input": user_input,
                    "num_questions": len(questions),
                    "answers_received": len(answers),
                },
            )

            spec_response = await self._call_llm(spec_context)

            # Log interaction
            result = AgentResult(
                output=spec_response,
                tokens_used=0,  # Would be tracked by LLM provider
                duration=time.time() - start_time,
            )
            self._log_interaction(spec_context, result)

            return result

        except Exception as e:
            logger.error(f"Spec gathering failed: {e}")
            raise RuntimeError(f"Spec gathering failed: {e}") from e

    async def execute_issue_creation(
        self, spec: str, epic_id: int
    ) -> List[int]:
        """
        Split specification into GitHub issues.

        Creates GitHub issues from spec, respecting ABD template guidelines
        and the ~20 changes per issue limit.

        Args:
            spec: Comprehensive specification text
            epic_id: Epic (milestone) ID to associate issues with

        Returns:
            List of created issue numbers

        Raises:
            RuntimeError: If issue creation fails
        """
        import time

        start_time = time.time()

        try:
            issue_manager = self._get_issue_manager()

            # Parse spec to identify issues
            split_context = AgentContext(
                goal="Split specification into individual issues",
                instructions=f"Specification:\n{spec}\n\nSplit into focused, actionable issues. Each issue should be ~20 changes max.",
                behavior_spec="Format each issue as:\n[ISSUE_START]\nTitle: ...\nBody: ...\n[ISSUE_END]",
                memory_context={"epic_id": epic_id},
            )

            split_response = await self._call_llm(split_context)

            # Extract issues from response
            issues = self._extract_issues(split_response)
            created_issue_numbers = []

            # Create each issue on GitHub
            for issue in issues:
                try:
                    issue_num = issue_manager.create_issue(
                        title=issue.get("title", "Untitled Issue"),
                        body=issue.get("body", ""),
                        labels=["abd-generated"],
                        milestone_id=epic_id,
                    )
                    created_issue_numbers.append(issue_num)
                    logger.info(f"Created GitHub issue #{issue_num}")
                except Exception as e:
                    logger.warning(f"Failed to create issue: {e}")

            # Log interaction
            result = AgentResult(
                output=f"Created {len(created_issue_numbers)} issues: {created_issue_numbers}",
                files_changed=[],
                commands_run=["github:create_issue"] * len(created_issue_numbers),
                duration=time.time() - start_time,
            )
            self._log_interaction(split_context, result)

            return created_issue_numbers

        except Exception as e:
            logger.error(f"Issue creation failed: {e}")
            raise RuntimeError(f"Issue creation failed: {e}") from e

    def _extract_questions(self, response: str) -> List[str]:
        """
        Extract clarifying questions from LLM response.

        Args:
            response: LLM response text

        Returns:
            List of question strings
        """
        questions = []
        lines = response.split("\n")

        for line in lines:
            line = line.strip()
            if line and (
                line.startswith("Q:") or line.startswith("-") and "?" in line
            ):
                # Clean up the question
                question = line.replace("Q:", "").replace("- ", "").strip()
                if question:
                    questions.append(question)

        return questions

    def _extract_issues(self, response: str) -> List[dict]:
        """
        Extract issue definitions from split response.

        Expected format: [ISSUE_START] ... [ISSUE_END]

        Args:
            response: LLM response with issue blocks

        Returns:
            List of issue dictionaries with title and body
        """
        issues = []
        blocks = response.split("[ISSUE_START]")

        for block in blocks[1:]:  # Skip first split before any block
            if "[ISSUE_END]" in block:
                content = block.split("[ISSUE_END]")[0].strip()
                issue = self._parse_issue_block(content)
                if issue:
                    issues.append(issue)

        return issues

    def _parse_issue_block(self, block: str) -> dict:
        """
        Parse a single issue block.

        Args:
            block: Issue block content

        Returns:
            Dictionary with title and body, or empty dict if invalid
        """
        lines = block.split("\n")
        issue = {"title": "", "body": ""}

        for line in lines:
            if line.startswith("Title:"):
                issue["title"] = line.replace("Title:", "").strip()
            elif line.startswith("Body:"):
                # Everything after Body: is the body
                idx = block.find("Body:")
                if idx != -1:
                    issue["body"] = block[idx + 5 :].strip()
                break

        return issue if issue["title"] else {}
