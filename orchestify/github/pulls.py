"""Pull request management for ABD orchestration engine."""

from typing import Optional, Dict, Any, List
from github.GithubException import GithubException
from github.PullRequest import PullRequest
from orchestify.github.client import GitHubClient


class PullRequestManager:
    """
    Manage GitHub pull requests with ABD-specific templates and operations.

    Attributes:
        client: GitHubClient instance
    """

    def __init__(self, client: GitHubClient) -> None:
        """
        Initialize pull request manager.

        Args:
            client: Authenticated GitHubClient instance
        """
        self.client = client

    def create_pr(
        self,
        title: str,
        body: str,
        head_branch: str,
        base_branch: str = "main",
        issue_number: Optional[int] = None,
    ) -> int:
        """
        Create a new pull request.

        Args:
            title: PR title
            body: PR body/description
            head_branch: Feature branch to merge from
            base_branch: Target branch to merge into (default: "main")
            issue_number: Issue number to link (optional, adds "Closes #N" to body)

        Returns:
            Pull request number

        Raises:
            GithubException: If PR creation fails
        """
        try:
            repo = self.client.get_repo()

            # Add issue reference if provided
            if issue_number is not None:
                body = f"{body}\n\nCloses #{issue_number}"

            pr = repo.create_pull(
                title=title,
                body=body,
                head=head_branch,
                base=base_branch,
            )

            return pr.number

        except GithubException as e:
            raise GithubException(
                status=e.status,
                headers=e.headers,
                data={"message": f"Failed to create PR: {str(e)}"},
            ) from e

    def get_pr(self, pr_number: int) -> Dict[str, Any]:
        """
        Get pull request details.

        Args:
            pr_number: PR number to retrieve

        Returns:
            Dictionary with PR details (title, body, state, author, etc.)

        Raises:
            GithubException: If PR cannot be retrieved
        """
        try:
            repo = self.client.get_repo()
            pr = repo.get_pull(pr_number)

            return {
                "number": pr.number,
                "title": pr.title,
                "body": pr.body,
                "state": pr.state,
                "author": pr.user.login,
                "head_branch": pr.head.ref,
                "base_branch": pr.base.ref,
                "created_at": pr.created_at.isoformat(),
                "updated_at": pr.updated_at.isoformat(),
                "merged": pr.merged,
                "merge_commit_sha": pr.merge_commit_sha,
                "commits": pr.commits,
                "changed_files": pr.changed_files,
                "additions": pr.additions,
                "deletions": pr.deletions,
                "url": pr.html_url,
            }

        except GithubException as e:
            raise GithubException(
                status=e.status,
                headers=e.headers,
                data={"message": f"Failed to get PR #{pr_number}: {str(e)}"},
            ) from e

    def add_review_comment(
        self,
        pr_number: int,
        body: str,
        path: Optional[str] = None,
        line: Optional[int] = None,
    ) -> int:
        """
        Add a comment to a PR.

        If path and line are provided, adds inline comment; otherwise adds general comment.

        Args:
            pr_number: PR number to comment on
            body: Comment body
            path: File path for inline comment (optional)
            line: Line number for inline comment (optional)

        Returns:
            Comment ID

        Raises:
            GithubException: If comment creation fails
            ValueError: If path provided without line or vice versa
        """
        try:
            if (path is None and line is not None) or (path is not None and line is None):
                raise ValueError("Both path and line must be provided together")

            repo = self.client.get_repo()
            pr = repo.get_pull(pr_number)

            if path and line:
                # Inline review comment
                comment = pr.create_review_comment(body=body, commit_id=pr.head.sha, path=path, line=line)
            else:
                # General PR comment
                comment = pr.create_issue_comment(body)

            return comment.id

        except GithubException as e:
            raise GithubException(
                status=e.status,
                headers=e.headers,
                data={
                    "message": f"Failed to add comment to PR #{pr_number}: {str(e)}"
                },
            ) from e

    def add_comment(self, pr_number: int, body: str) -> int:
        """
        Add a general comment to a PR (not a review).

        Args:
            pr_number: PR number to comment on
            body: Comment body

        Returns:
            Comment ID

        Raises:
            GithubException: If comment creation fails
        """
        try:
            repo = self.client.get_repo()
            pr = repo.get_pull(pr_number)
            comment = pr.create_issue_comment(body)
            return comment.id

        except GithubException as e:
            raise GithubException(
                status=e.status,
                headers=e.headers,
                data={
                    "message": f"Failed to add comment to PR #{pr_number}: {str(e)}"
                },
            ) from e

    def get_review_comments(self, pr_number: int) -> List[Dict[str, Any]]:
        """
        Get all review comments on a PR.

        Args:
            pr_number: PR number to get comments from

        Returns:
            List of review comment dictionaries

        Raises:
            GithubException: If comments cannot be retrieved
        """
        try:
            repo = self.client.get_repo()
            pr = repo.get_pull(pr_number)

            comments = []
            for comment in pr.get_reviews():
                for review_comment in comment.get_comments():
                    comments.append(
                        {
                            "id": review_comment.id,
                            "body": review_comment.body,
                            "user": review_comment.user.login,
                            "path": review_comment.path,
                            "line": review_comment.line,
                            "created_at": review_comment.created_at.isoformat(),
                            "updated_at": review_comment.updated_at.isoformat(),
                            "url": review_comment.html_url,
                        }
                    )

            return comments

        except GithubException as e:
            raise GithubException(
                status=e.status,
                headers=e.headers,
                data={
                    "message": f"Failed to get review comments for PR #{pr_number}: {str(e)}"
                },
            ) from e

    def get_diff(self, pr_number: int) -> str:
        """
        Get the diff for a PR.

        Args:
            pr_number: PR number to get diff for

        Returns:
            Diff content as string

        Raises:
            RuntimeError: If diff retrieval fails
        """
        try:
            return self.client._run_gh(
                ["pr", "diff", str(pr_number), "--repo", self.client.repo_full_name]
            )
        except RuntimeError as e:
            raise RuntimeError(f"Failed to get diff for PR #{pr_number}: {str(e)}") from e

    def merge_pr(self, pr_number: int, merge_method: str = "squash") -> bool:
        """
        Merge a pull request.

        Args:
            pr_number: PR number to merge
            merge_method: Merge method - "squash", "rebase", or "merge" (default: "squash")

        Returns:
            True if merge successful, False if PR was already merged

        Raises:
            GithubException: If merge fails
            ValueError: If merge_method is invalid
        """
        try:
            if merge_method not in ("squash", "rebase", "merge"):
                raise ValueError(
                    "merge_method must be 'squash', 'rebase', or 'merge'"
                )

            repo = self.client.get_repo()
            pr = repo.get_pull(pr_number)

            # Check if already merged
            if pr.merged:
                return False

            # Perform merge
            pr.merge(merge_method=merge_method)
            return True

        except GithubException as e:
            raise GithubException(
                status=e.status,
                headers=e.headers,
                data={"message": f"Failed to merge PR #{pr_number}: {str(e)}"},
            ) from e

    def request_changes(self, pr_number: int, body: str) -> Dict[str, Any]:
        """
        Post a "request changes" review on a PR.

        Args:
            pr_number: PR number to review
            body: Review body/message

        Returns:
            Review details dictionary

        Raises:
            GithubException: If review creation fails
        """
        try:
            repo = self.client.get_repo()
            pr = repo.get_pull(pr_number)
            review = pr.create_review(body=body, event="REQUEST_CHANGES")

            return {
                "id": review.id,
                "body": review.body,
                "state": review.state,
                "user": review.user.login,
                "submitted_at": (
                    review.submitted_at.isoformat() if review.submitted_at else None
                ),
                "url": review.html_url,
            }

        except GithubException as e:
            raise GithubException(
                status=e.status,
                headers=e.headers,
                data={
                    "message": f"Failed to request changes on PR #{pr_number}: {str(e)}"
                },
            ) from e

    def approve(self, pr_number: int, body: str = "") -> Dict[str, Any]:
        """
        Post an "approve" review on a PR.

        Args:
            pr_number: PR number to approve
            body: Review body/message (optional)

        Returns:
            Review details dictionary

        Raises:
            GithubException: If review creation fails
        """
        try:
            repo = self.client.get_repo()
            pr = repo.get_pull(pr_number)
            review = pr.create_review(body=body, event="APPROVE")

            return {
                "id": review.id,
                "body": review.body,
                "state": review.state,
                "user": review.user.login,
                "submitted_at": (
                    review.submitted_at.isoformat() if review.submitted_at else None
                ),
                "url": review.html_url,
            }

        except GithubException as e:
            raise GithubException(
                status=e.status,
                headers=e.headers,
                data={"message": f"Failed to approve PR #{pr_number}: {str(e)}"},
            ) from e

    @staticmethod
    def format_pr_body(context: Dict[str, Any]) -> str:
        """
        Format PR body using ABD template.

        Args:
            context: Dictionary with keys:
                - agent_directive: Role and behavior instructions
                - goal: Clear, concise goal
                - context_text: Background information
                - changes: List of changes made
                - testing: Testing approach
                - related_issues: Related issue numbers
                - breaking_changes: Any breaking changes
                - migration_guide: Migration guide if needed
                - touches: List of affected files/modules
                - risks: List of identified risks

        Returns:
            Formatted PR body string
        """
        body_parts = []

        if context.get("agent_directive"):
            body_parts.append(f"## Agent Directive\n\n{context['agent_directive']}")

        if context.get("goal"):
            body_parts.append(f"## Goal\n\n{context['goal']}")

        if context.get("context_text"):
            body_parts.append(f"## Context\n\n{context['context_text']}")

        if context.get("changes"):
            changes = context["changes"]
            if isinstance(changes, list):
                changes_str = "\n".join(f"- {change}" for change in changes)
            else:
                changes_str = changes
            body_parts.append(f"## Changes\n\n{changes_str}")

        if context.get("testing"):
            body_parts.append(f"## Testing\n\n{context['testing']}")

        if context.get("related_issues"):
            issues = context["related_issues"]
            if isinstance(issues, list):
                issues_str = "\n".join(f"- Closes #{issue}" for issue in issues)
            else:
                issues_str = issues
            body_parts.append(f"## Related Issues\n\n{issues_str}")

        if context.get("breaking_changes"):
            body_parts.append(
                f"## Breaking Changes\n\n{context['breaking_changes']}"
            )

        if context.get("migration_guide"):
            body_parts.append(f"## Migration Guide\n\n{context['migration_guide']}")

        # ABD specific section
        body_parts.append(
            """## Done Checklist (ABD)

- [ ] Code review complete
- [ ] Tests passing
- [ ] Documentation updated
- [ ] Evidence documented"""
        )

        if context.get("touches"):
            touches = context["touches"]
            if isinstance(touches, list):
                touches_str = "\n".join(f"- {touch}" for touch in touches)
            else:
                touches_str = touches
            body_parts.append(f"## Touches\n\n{touches_str}")

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
- Test all changes before submission
- Ensure CI/CD passes"""
        )

        return "\n\n".join(body_parts)
