"""Label management for ABD orchestration engine."""

from typing import Dict, List
from github.GithubException import GithubException
from orchestify.github.client import GitHubClient


# Standard ABD labels with color codes
STANDARD_LABELS: Dict[str, str] = {
    "frontend": "61DAFB",  # React blue
    "backend": "68BC71",  # green
    "ios": "000000",  # black
    "android": "3DDC84",  # Android green
    "abd-core": "9C27B0",  # purple
    "agent-behavior": "FF9800",  # orange
    "prompt-change": "F44336",  # red
    "evidence-required": "FFC107",  # amber
    "recycle-output": "4CAF50",  # green
    "high-risk": "B71C1C",  # dark red
    "conflict-detected": "FF5722",  # deep orange
    "anti-pattern": "795548",  # brown
    "ready-for-review": "2196F3",  # blue
    "ready-for-qa": "00BCD4",  # cyan
    "approved": "4CAF50",  # green
    "escalated": "E91E63",  # pink
}


class LabelManager:
    """
    Manage GitHub labels with ABD-specific standard labels.

    Attributes:
        client: GitHubClient instance
    """

    def __init__(self, client: GitHubClient) -> None:
        """
        Initialize label manager.

        Args:
            client: Authenticated GitHubClient instance
        """
        self.client = client

    def ensure_labels(self) -> List[str]:
        """
        Create all required standard labels if they don't exist.

        Returns:
            List of created label names (not including existing ones)

        Raises:
            GithubException: If label creation fails
        """
        try:
            repo = self.client.get_repo()
            created_labels = []

            # Get existing labels
            existing_labels = {label.name for label in repo.get_labels()}

            # Create missing labels
            for label_name, color in STANDARD_LABELS.items():
                if label_name not in existing_labels:
                    repo.create_label(name=label_name, color=color)
                    created_labels.append(label_name)

            return created_labels

        except GithubException as e:
            raise GithubException(
                status=e.status,
                headers=e.headers,
                data={"message": f"Failed to ensure labels: {str(e)}"},
            ) from e

    def add_labels(self, issue_number: int, labels: List[str]) -> None:
        """
        Add labels to an issue.

        Args:
            issue_number: Issue number to label
            labels: List of label names to add

        Raises:
            GithubException: If label addition fails
        """
        try:
            repo = self.client.get_repo()
            issue = repo.get_issue(issue_number)

            # Get current labels
            current_labels = {label.name for label in issue.labels}

            # Add new labels (avoiding duplicates)
            labels_to_add = [label for label in labels if label not in current_labels]

            if labels_to_add:
                # Create label objects
                label_objects = []
                for label_name in labels_to_add:
                    try:
                        label_obj = repo.get_label(label_name)
                        label_objects.append(label_obj)
                    except GithubException:
                        # Label doesn't exist, try to create it
                        if label_name in STANDARD_LABELS:
                            label_obj = repo.create_label(
                                name=label_name, color=STANDARD_LABELS[label_name]
                            )
                            label_objects.append(label_obj)

                # Add all labels at once
                if label_objects:
                    all_labels = list(issue.labels) + label_objects
                    issue.set_labels(*all_labels)

        except GithubException as e:
            raise GithubException(
                status=e.status,
                headers=e.headers,
                data={
                    "message": f"Failed to add labels to issue #{issue_number}: {str(e)}"
                },
            ) from e

    def remove_label(self, issue_number: int, label: str) -> None:
        """
        Remove a label from an issue.

        Args:
            issue_number: Issue number to remove label from
            label: Label name to remove

        Raises:
            GithubException: If label removal fails
        """
        try:
            repo = self.client.get_repo()
            issue = repo.get_issue(issue_number)
            issue.remove_from_labels(label)

        except GithubException as e:
            raise GithubException(
                status=e.status,
                headers=e.headers,
                data={
                    "message": f"Failed to remove label from issue #{issue_number}: {str(e)}"
                },
            ) from e

    def get_labels(self, issue_number: int) -> List[str]:
        """
        Get all labels on an issue.

        Args:
            issue_number: Issue number to get labels from

        Returns:
            List of label names

        Raises:
            GithubException: If labels cannot be retrieved
        """
        try:
            repo = self.client.get_repo()
            issue = repo.get_issue(issue_number)
            return [label.name for label in issue.labels]

        except GithubException as e:
            raise GithubException(
                status=e.status,
                headers=e.headers,
                data={
                    "message": f"Failed to get labels for issue #{issue_number}: {str(e)}"
                },
            ) from e
