"""Issue management for ABD orchestration engine."""

from typing import Optional, Dict, Any, List
from github.GithubException import GithubException
from orchestify.github.client import GitHubClient


class IssueManager:
    """
    Manage GitHub issues with ABD-specific templates and operations.

    Attributes:
        client: GitHubClient instance
    """

    def __init__(self, client: GitHubClient) -> None:
        """
        Initialize issue manager.

        Args:
            client: Authenticated GitHubClient instance
        """
        self.client = client

    def create_issue(
        self,
        title: str,
        body: str,
        labels: Optional[List[str]] = None,
        milestone_id: Optional[int] = None,
    ) -> int:
        """
        Create a new GitHub issue.

        Args:
            title: Issue title
            body: Issue body/description
            labels: List of label names to apply (optional)
            milestone_id: Milestone (epic) ID (optional)

        Returns:
            Issue number (unique identifier)

        Raises:
            GithubException: If issue creation fails
        """
        try:
            repo = self.client.get_repo()

            # Prepare issue parameters
            issue_params = {"title": title, "body": body}

            if labels:
                issue_params["labels"] = labels

            if milestone_id is not None:
                # Get milestone object
                milestones = list(repo.get_milestones())
                milestone_obj = next(
                    (m for m in milestones if m.number == milestone_id),
                    None,
                )
                if milestone_obj:
                    issue_params["milestone"] = milestone_obj

            issue = repo.create_issue(**issue_params)
            return issue.number

        except GithubException as e:
            raise GithubException(
                status=e.status,
                headers=e.headers,
                data={"message": f"Failed to create issue: {str(e)}"},
            ) from e

    def update_issue(
        self,
        issue_number: int,
        title: Optional[str] = None,
        body: Optional[str] = None,
        labels: Optional[List[str]] = None,
        state: Optional[str] = None,
    ) -> None:
        """
        Update an existing issue.

        Args:
            issue_number: Issue number to update
            title: New title (optional)
            body: New body (optional)
            labels: New list of labels (optional)
            state: New state - "open" or "closed" (optional)

        Raises:
            GithubException: If issue update fails
        """
        try:
            repo = self.client.get_repo()
            issue = repo.get_issue(issue_number)

            update_params = {}
            if title is not None:
                update_params["title"] = title
            if body is not None:
                update_params["body"] = body
            if labels is not None:
                update_params["labels"] = labels
            if state is not None:
                if state not in ("open", "closed"):
                    raise ValueError("State must be 'open' or 'closed'")
                update_params["state"] = state

            issue.edit(**update_params)

        except GithubException as e:
            raise GithubException(
                status=e.status,
                headers=e.headers,
                data={"message": f"Failed to update issue #{issue_number}: {str(e)}"},
            ) from e

    def close_issue(self, issue_number: int) -> None:
        """
        Close an issue.

        Args:
            issue_number: Issue number to close

        Raises:
            GithubException: If close operation fails
        """
        self.update_issue(issue_number, state="closed")

    def get_issue(self, issue_number: int) -> Dict[str, Any]:
        """
        Get issue details.

        Args:
            issue_number: Issue number to retrieve

        Returns:
            Dictionary with issue details (title, body, state, labels, etc.)

        Raises:
            GithubException: If issue cannot be retrieved
        """
        try:
            repo = self.client.get_repo()
            issue = repo.get_issue(issue_number)

            return {
                "number": issue.number,
                "title": issue.title,
                "body": issue.body,
                "state": issue.state,
                "labels": [label.name for label in issue.labels],
                "milestone": issue.milestone.title if issue.milestone else None,
                "milestone_id": issue.milestone.number if issue.milestone else None,
                "created_at": issue.created_at.isoformat(),
                "updated_at": issue.updated_at.isoformat(),
                "url": issue.html_url,
            }

        except GithubException as e:
            raise GithubException(
                status=e.status,
                headers=e.headers,
                data={"message": f"Failed to get issue #{issue_number}: {str(e)}"},
            ) from e

    def list_issues(
        self,
        milestone_id: Optional[int] = None,
        labels: Optional[List[str]] = None,
        state: str = "open",
    ) -> List[Dict[str, Any]]:
        """
        List issues with optional filtering.

        Args:
            milestone_id: Filter by milestone ID (optional)
            labels: Filter by labels (optional)
            state: Filter by state - "open", "closed", or "all" (default: "open")

        Returns:
            List of issue dictionaries

        Raises:
            GithubException: If list operation fails
        """
        try:
            repo = self.client.get_repo()

            # Build filters
            kwargs = {"state": state}
            if milestone_id is not None:
                milestones = list(repo.get_milestones())
                milestone_obj = next(
                    (m for m in milestones if m.number == milestone_id),
                    None,
                )
                if milestone_obj:
                    kwargs["milestone"] = milestone_obj

            if labels:
                kwargs["labels"] = [repo.get_label(label) for label in labels]

            issues = repo.get_issues(**kwargs)

            result = []
            for issue in issues:
                result.append(
                    {
                        "number": issue.number,
                        "title": issue.title,
                        "body": issue.body,
                        "state": issue.state,
                        "labels": [label.name for label in issue.labels],
                        "milestone": issue.milestone.title if issue.milestone else None,
                        "milestone_id": (
                            issue.milestone.number if issue.milestone else None
                        ),
                        "created_at": issue.created_at.isoformat(),
                        "updated_at": issue.updated_at.isoformat(),
                        "url": issue.html_url,
                    }
                )

            return result

        except GithubException as e:
            raise GithubException(
                status=e.status,
                headers=e.headers,
                data={"message": f"Failed to list issues: {str(e)}"},
            ) from e

    def add_comment(self, issue_number: int, body: str) -> int:
        """
        Add a comment to an issue.

        Args:
            issue_number: Issue number to comment on
            body: Comment body

        Returns:
            Comment ID

        Raises:
            GithubException: If comment creation fails
        """
        try:
            repo = self.client.get_repo()
            issue = repo.get_issue(issue_number)
            comment = issue.create_comment(body)
            return comment.id

        except GithubException as e:
            raise GithubException(
                status=e.status,
                headers=e.headers,
                data={
                    "message": f"Failed to add comment to issue #{issue_number}: {str(e)}"
                },
            ) from e

    def get_comments(self, issue_number: int) -> List[Dict[str, Any]]:
        """
        Get all comments on an issue.

        Args:
            issue_number: Issue number to get comments from

        Returns:
            List of comment dictionaries

        Raises:
            GithubException: If comments cannot be retrieved
        """
        try:
            repo = self.client.get_repo()
            issue = repo.get_issue(issue_number)

            comments = []
            for comment in issue.get_comments():
                comments.append(
                    {
                        "id": comment.id,
                        "body": comment.body,
                        "user": comment.user.login,
                        "created_at": comment.created_at.isoformat(),
                        "updated_at": comment.updated_at.isoformat(),
                        "url": comment.html_url,
                    }
                )

            return comments

        except GithubException as e:
            raise GithubException(
                status=e.status,
                headers=e.headers,
                data={
                    "message": f"Failed to get comments for issue #{issue_number}: {str(e)}"
                },
            ) from e

    @staticmethod
    def format_issue_body(context: Dict[str, Any]) -> str:
        """
        Format issue body using ABD template.

        Args:
            context: Dictionary with keys:
                - agent_directive: Role and behavior instructions
                - goal: Clear, concise goal
                - context_text: Background information
                - instructions: List of step-by-step instructions
                - behavior_scenarios: List of scenario specifications
                - acceptance_criteria: List of criteria with checkboxes
                - touches: List of affected files/modules
                - dependencies: List of issue numbers
                - risks: List of identified risks

        Returns:
            Formatted issue body string
        """
        body_parts = []

        if context.get("agent_directive"):
            body_parts.append(f"## Agent Directive\n\n{context['agent_directive']}")

        if context.get("goal"):
            body_parts.append(f"## Goal\n\n{context['goal']}")

        if context.get("context_text"):
            body_parts.append(f"## Context\n\n{context['context_text']}")

        if context.get("instructions"):
            instructions = context["instructions"]
            if isinstance(instructions, list):
                instructions_str = "\n".join(
                    f"{i+1}. {inst}" for i, inst in enumerate(instructions)
                )
            else:
                instructions_str = instructions
            body_parts.append(f"## Instructions\n\n{instructions_str}")

        if context.get("behavior_scenarios"):
            scenarios = context["behavior_scenarios"]
            if isinstance(scenarios, list):
                scenarios_str = "\n".join(f"- {scenario}" for scenario in scenarios)
            else:
                scenarios_str = scenarios
            body_parts.append(f"## Behavior Specification\n\n{scenarios_str}")

        if context.get("acceptance_criteria"):
            criteria = context["acceptance_criteria"]
            if isinstance(criteria, list):
                criteria_str = "\n".join(f"- [ ] {criterion}" for criterion in criteria)
            else:
                criteria_str = criteria
            body_parts.append(f"## Acceptance Criteria\n\n{criteria_str}")

        # ABD specific section
        body_parts.append(
            """## Done Checklist (ABD)

- [ ] Prompt executed
- [ ] Evidence exists
- [ ] Scorecard filled
- [ ] Recycle output recorded"""
        )

        if context.get("touches"):
            touches = context["touches"]
            if isinstance(touches, list):
                touches_str = "\n".join(f"- {touch}" for touch in touches)
            else:
                touches_str = touches
            body_parts.append(f"## Touches\n\n{touches_str}")

        if context.get("dependencies"):
            dependencies = context["dependencies"]
            if isinstance(dependencies, list):
                deps_str = "\n".join(f"- #{dep}" for dep in dependencies)
            else:
                deps_str = dependencies
            body_parts.append(f"## Dependencies\n\n{deps_str}")

        if context.get("risks"):
            risks = context["risks"]
            if isinstance(risks, list):
                risks_str = "\n".join(f"- {risk}" for risk in risks)
            else:
                risks_str = risks
            body_parts.append(f"## Risks\n\n{risks_str}")

        # Add global rules
        body_parts.append(
            """## Global Rules

- Follow output format exactly
- Propose evidence before implementation
- Ask up to 3 questions if critical info missing, then stop"""
        )

        return "\n\n".join(body_parts)
