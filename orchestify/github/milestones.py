"""Milestone/Epic management for ABD orchestration engine."""

from typing import Optional, Dict, Any, List
from datetime import datetime
from github.GithubException import GithubException
from orchestify.github.client import GitHubClient


class MilestoneManager:
    """
    Manage GitHub milestones (epics) with progress tracking.

    Attributes:
        client: GitHubClient instance
    """

    def __init__(self, client: GitHubClient) -> None:
        """
        Initialize milestone manager.

        Args:
            client: Authenticated GitHubClient instance
        """
        self.client = client

    def create_milestone(
        self,
        title: str,
        description: Optional[str] = None,
        due_date: Optional[str] = None,
    ) -> int:
        """
        Create a new milestone (epic).

        Args:
            title: Milestone title
            description: Milestone description (optional)
            due_date: Due date in ISO format (YYYY-MM-DD) (optional)

        Returns:
            Milestone number (ID)

        Raises:
            GithubException: If milestone creation fails
            ValueError: If due_date format is invalid
        """
        try:
            repo = self.client.get_repo()

            # Validate due_date format if provided
            if due_date:
                try:
                    datetime.fromisoformat(due_date)
                except ValueError:
                    raise ValueError(
                        f"Invalid due_date format: {due_date}. Expected YYYY-MM-DD"
                    )

            milestone_params = {"title": title}
            if description:
                milestone_params["description"] = description
            if due_date:
                milestone_params["due_on"] = due_date

            milestone = repo.create_milestone(**milestone_params)
            return milestone.number

        except GithubException as e:
            raise GithubException(
                status=e.status,
                headers=e.headers,
                data={"message": f"Failed to create milestone: {str(e)}"},
            ) from e

    def get_milestone(self, milestone_id: int) -> Dict[str, Any]:
        """
        Get milestone details.

        Args:
            milestone_id: Milestone number/ID

        Returns:
            Dictionary with milestone details

        Raises:
            GithubException: If milestone cannot be retrieved
        """
        try:
            repo = self.client.get_repo()
            milestone = repo.get_milestone(milestone_id)

            return {
                "number": milestone.number,
                "title": milestone.title,
                "description": milestone.description,
                "state": milestone.state,
                "open_issues": milestone.open_issues,
                "closed_issues": milestone.closed_issues,
                "created_at": milestone.created_at.isoformat(),
                "updated_at": milestone.updated_at.isoformat(),
                "due_on": milestone.due_on.isoformat() if milestone.due_on else None,
                "url": milestone.html_url,
            }

        except GithubException as e:
            raise GithubException(
                status=e.status,
                headers=e.headers,
                data={"message": f"Failed to get milestone #{milestone_id}: {str(e)}"},
            ) from e

    def close_milestone(self, milestone_id: int) -> None:
        """
        Close a milestone.

        Args:
            milestone_id: Milestone number/ID to close

        Raises:
            GithubException: If close operation fails
        """
        try:
            repo = self.client.get_repo()
            milestone = repo.get_milestone(milestone_id)
            milestone.edit(state="closed")

        except GithubException as e:
            raise GithubException(
                status=e.status,
                headers=e.headers,
                data={
                    "message": f"Failed to close milestone #{milestone_id}: {str(e)}"
                },
            ) from e

    def list_milestones(self, state: str = "open") -> List[Dict[str, Any]]:
        """
        List milestones with optional filtering.

        Args:
            state: Filter by state - "open", "closed", or "all" (default: "open")

        Returns:
            List of milestone dictionaries

        Raises:
            GithubException: If list operation fails
            ValueError: If state is invalid
        """
        try:
            if state not in ("open", "closed", "all"):
                raise ValueError("state must be 'open', 'closed', or 'all'")

            repo = self.client.get_repo()
            milestones = repo.get_milestones(state=state)

            result = []
            for milestone in milestones:
                result.append(
                    {
                        "number": milestone.number,
                        "title": milestone.title,
                        "description": milestone.description,
                        "state": milestone.state,
                        "open_issues": milestone.open_issues,
                        "closed_issues": milestone.closed_issues,
                        "created_at": milestone.created_at.isoformat(),
                        "updated_at": milestone.updated_at.isoformat(),
                        "due_on": (
                            milestone.due_on.isoformat() if milestone.due_on else None
                        ),
                        "url": milestone.html_url,
                    }
                )

            return result

        except GithubException as e:
            raise GithubException(
                status=e.status,
                headers=e.headers,
                data={"message": f"Failed to list milestones: {str(e)}"},
            ) from e

    def get_progress(self, milestone_id: int) -> Dict[str, Any]:
        """
        Get progress metrics for a milestone.

        Args:
            milestone_id: Milestone number/ID

        Returns:
            Dictionary with progress metrics:
                - total: Total issues
                - open: Number of open issues
                - closed: Number of closed issues
                - percent_complete: Percentage complete (0-100)

        Raises:
            GithubException: If progress cannot be retrieved
        """
        try:
            repo = self.client.get_repo()
            milestone = repo.get_milestone(milestone_id)

            total = milestone.open_issues + milestone.closed_issues
            percent_complete = (
                0
                if total == 0
                else round((milestone.closed_issues / total) * 100, 1)
            )

            return {
                "total": total,
                "open": milestone.open_issues,
                "closed": milestone.closed_issues,
                "percent_complete": percent_complete,
            }

        except GithubException as e:
            raise GithubException(
                status=e.status,
                headers=e.headers,
                data={
                    "message": f"Failed to get progress for milestone #{milestone_id}: {str(e)}"
                },
            ) from e
