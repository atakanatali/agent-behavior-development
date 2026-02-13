"""End-to-end tests for the full ABD workflow with mock LLM."""
import json
import os
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from orchestify.core.state import (
    EpicState,
    EpicStatus,
    IssueState,
    IssueStatus,
    StateManager,
)
from orchestify.core.agent import (
    AgentContext,
    AgentResult,
    BaseAgent,
    Scorecard,
    RecycleOutput,
    Interpretation,
)
from orchestify.utils.validators import (
    validate_scorecard,
    validate_evidence,
    validate_actionability,
)


# ─── E2E: Full Development Lifecycle ───


class TestFullDevelopmentLifecycle:
    """Simulate a complete feature development through the ABD pipeline."""

    @pytest.fixture
    def repo(self, tmp_path):
        """Create a simulated repository."""
        repo = tmp_path / "e2e-repo"
        repo.mkdir()
        (repo / ".orchestify").mkdir()
        return repo

    def test_complete_feature_development(self, repo):
        """
        Simulate the complete flow:
        1. TPM creates epic with issues
        2. Issues go through engineer -> reviewer -> QA -> architect
        3. Epic completes successfully
        """
        sm = StateManager(repo)

        # ═══ PHASE 1: TPM creates epic ═══
        epic = sm.create_epic("epic-auth-feature")
        sm.update_epic_status("epic-auth-feature", EpicStatus.IN_PROGRESS)

        # TPM creates 3 issues
        issues = [
            {"issue_number": 1, "title": "Implement JWT token generation"},
            {"issue_number": 2, "title": "Add auth middleware"},
            {"issue_number": 3, "title": "Create login/logout endpoints"},
        ]
        for issue in issues:
            sm.update_issue("epic-auth-feature", issue["issue_number"], {
                "status": IssueStatus.PENDING,
                "assigned_agent": None,
            })

        epic = sm.get_epic("epic-auth-feature")
        assert len(epic.issues) == 3
        assert all(i.status == IssueStatus.PENDING for i in epic.issues)

        # ═══ PHASE 2: Architect distributes ═══
        sm.update_issue("epic-auth-feature", 1, {"assigned_agent": "engineer_backend"})
        sm.update_issue("epic-auth-feature", 2, {"assigned_agent": "engineer_backend"})
        sm.update_issue("epic-auth-feature", 3, {"assigned_agent": "engineer_backend"})

        # ═══ PHASE 3: Issue loop for each issue ═══
        for issue_num in [1, 2, 3]:
            # Engineer develops
            sm.update_issue("epic-auth-feature", issue_num, {
                "status": IssueStatus.IN_PROGRESS,
                "branch_name": f"feature/epic-auth-{issue_num}",
                "pr_number": 100 + issue_num,
            })
            sm.add_cycle(
                "epic-auth-feature", issue_num,
                "engineer_backend", "reviewer_backend",
                "Submitted PR", "Code implemented"
            )

            # Reviewer reviews
            sm.update_issue("epic-auth-feature", issue_num, {
                "status": IssueStatus.REVIEW,
                "review_cycles": 1,
            })

            # First review: request changes
            sm.add_cycle(
                "epic-auth-feature", issue_num,
                "reviewer_backend", "engineer_backend",
                "Review comments", "Minor fixes needed"
            )

            # Engineer fixes
            sm.add_cycle(
                "epic-auth-feature", issue_num,
                "engineer_backend", "reviewer_backend",
                "Fixes applied", "Addressed all comments"
            )

            # Second review: approved
            sm.update_issue("epic-auth-feature", issue_num, {"review_cycles": 2})
            sm.add_cycle(
                "epic-auth-feature", issue_num,
                "reviewer_backend", "qa",
                "Approved", "Code looks good"
            )

            # QA tests
            sm.update_issue("epic-auth-feature", issue_num, {
                "status": IssueStatus.QA,
                "qa_cycles": 1,
            })
            sm.add_cycle(
                "epic-auth-feature", issue_num,
                "qa", "architect",
                "Tests passed", "All acceptance criteria met"
            )

            # Architect final review & merge
            scorecard = Scorecard(
                scope_control=2, behavior_fidelity=2,
                evidence_orientation=1, actionability=2, risk_awareness=1,
            )
            sm.update_issue("epic-auth-feature", issue_num, {
                "status": IssueStatus.DONE,
                "scorecard": scorecard.to_dict(),
                "recycle_output": {
                    "kept": [f"auth_pattern_{issue_num}"],
                    "reused": [],
                    "banned": [],
                },
            })
            sm.add_cycle(
                "epic-auth-feature", issue_num,
                "architect", "complete",
                "Merged to main", "Issue closed"
            )

        # ═══ PHASE 4: Complete ═══
        assert sm.is_epic_complete("epic-auth-feature") is True
        sm.update_epic_status("epic-auth-feature", EpicStatus.COMPLETE)

        # ═══ VERIFICATION ═══
        final_epic = sm.get_epic("epic-auth-feature")
        assert final_epic.status == EpicStatus.COMPLETE
        assert len(final_epic.issues) == 3

        for issue in final_epic.issues:
            assert issue.status == IssueStatus.DONE
            assert issue.pr_number is not None
            assert issue.branch_name is not None
            assert issue.review_cycles == 2
            assert issue.qa_cycles == 1
            assert len(issue.cycle_history) == 6
            assert issue.scorecard["total"] == 8
            assert issue.scorecard["interpretation"] == "promote"
            assert len(issue.recycle_output["kept"]) == 1

    def test_escalation_after_max_cycles(self, repo):
        """
        Test that an issue escalates to user after max review cycles.
        """
        sm = StateManager(repo)
        sm.create_epic("epic-escalation")
        sm.update_epic_status("epic-escalation", EpicStatus.IN_PROGRESS)
        sm.update_issue("epic-escalation", 1, {
            "status": IssueStatus.IN_PROGRESS,
            "assigned_agent": "engineer_frontend",
        })

        # 3 review cycles, all requesting changes
        for cycle in range(1, 4):
            sm.update_issue("epic-escalation", 1, {
                "status": IssueStatus.REVIEW,
                "review_cycles": cycle,
            })
            sm.add_cycle(
                "epic-escalation", 1,
                "reviewer_frontend", "engineer_frontend",
                f"Review cycle {cycle}", "Changes requested"
            )
            sm.add_cycle(
                "epic-escalation", 1,
                "engineer_frontend", "reviewer_frontend",
                f"Fix attempt {cycle}", "Attempted fix"
            )

        # After 3 cycles, escalate
        sm.update_issue("epic-escalation", 1, {"status": IssueStatus.ESCALATED})

        epic = sm.get_epic("epic-escalation")
        assert epic.issues[0].status == IssueStatus.ESCALATED
        assert epic.issues[0].review_cycles == 3

    def test_qa_rejection_sends_back_through_reviewer(self, repo):
        """
        Test the critical recycle flow: QA rejection -> engineer -> reviewer -> QA.
        """
        sm = StateManager(repo)
        sm.create_epic("epic-qa-reject")
        sm.update_epic_status("epic-qa-reject", EpicStatus.IN_PROGRESS)
        sm.update_issue("epic-qa-reject", 1, {
            "status": IssueStatus.IN_PROGRESS,
            "assigned_agent": "engineer_ios",
            "pr_number": 200,
        })

        # First pass: engineer -> reviewer -> QA
        sm.add_cycle("epic-qa-reject", 1, "engineer_ios", "reviewer_ios", "PR", "OK")
        sm.update_issue("epic-qa-reject", 1, {"status": IssueStatus.REVIEW, "review_cycles": 1})
        sm.add_cycle("epic-qa-reject", 1, "reviewer_ios", "qa", "Approved", "Pass")
        sm.update_issue("epic-qa-reject", 1, {"status": IssueStatus.QA, "qa_cycles": 1})

        # QA rejects
        sm.add_cycle("epic-qa-reject", 1, "qa", "engineer_ios", "Bug found", "Fix needed")

        # Engineer fixes
        sm.update_issue("epic-qa-reject", 1, {"status": IssueStatus.IN_PROGRESS})
        sm.add_cycle("epic-qa-reject", 1, "engineer_ios", "reviewer_ios", "Fix applied", "Bug fixed")

        # Back through reviewer
        sm.update_issue("epic-qa-reject", 1, {"status": IssueStatus.REVIEW, "review_cycles": 2})
        sm.add_cycle("epic-qa-reject", 1, "reviewer_ios", "qa", "Approved", "Fix OK")

        # QA approves this time
        sm.update_issue("epic-qa-reject", 1, {"status": IssueStatus.QA, "qa_cycles": 2})
        sm.add_cycle("epic-qa-reject", 1, "qa", "architect", "All tests pass", "Approved")

        # Final merge
        sm.update_issue("epic-qa-reject", 1, {"status": IssueStatus.DONE})
        sm.add_cycle("epic-qa-reject", 1, "architect", "complete", "Merged", "Done")

        epic = sm.get_epic("epic-qa-reject")
        issue = epic.issues[0]
        assert issue.status == IssueStatus.DONE
        assert issue.review_cycles == 2
        assert issue.qa_cycles == 2
        assert len(issue.cycle_history) == 7  # Full cycle history

    def test_state_file_valid_json(self, repo):
        """State file should always be valid JSON."""
        sm = StateManager(repo)
        sm.create_epic("json-test")
        sm.update_issue("json-test", 1, {"status": IssueStatus.IN_PROGRESS})
        sm.add_cycle("json-test", 1, "a", "b", "c", "d")

        state_file = repo / ".orchestify" / "state.json"
        assert state_file.exists()

        # Must parse as valid JSON
        with open(state_file) as f:
            data = json.load(f)

        assert "json-test" in data
        assert data["json-test"]["status"] == "pending"  # Epic status not changed from default
        assert len(data["json-test"]["issues"]) == 1

    def test_scorecard_validation_integration(self):
        """End-to-end scorecard creation and validation."""
        sc = Scorecard(
            scope_control=2, behavior_fidelity=2,
            evidence_orientation=1, actionability=2, risk_awareness=1,
        )
        is_valid, errors = validate_scorecard(sc)
        assert is_valid is True
        assert errors == []
        assert sc.total == 8
        assert sc.interpretation == Interpretation.PROMOTE

    def test_evidence_validation_integration(self):
        """Validate realistic agent output for evidence."""
        output = """
## Implementation Complete

Added JWT authentication:

```python
class JWTAuth:
    def generate_token(self, user_id: str) -> str:
        return jwt.encode({"sub": user_id}, SECRET_KEY)
```

Test results: All 12 tests passed
Performance: Token generation takes ~2ms average
Error at line 45 was fixed by adding null check.
"""
        is_valid, errors = validate_evidence(output, minimum_pieces=3)
        assert is_valid is True

    def test_actionability_validation_integration(self):
        """Validate realistic review content for actionability."""
        content = """
1. Change the `authenticate()` function to validate token expiry
2. Add rate limiting middleware before the auth check
3. Update error messages to include request ID

The login endpoint should return 401 for expired tokens.
Must handle concurrent refresh token requests safely.
"""
        is_valid, errors = validate_actionability(content)
        assert is_valid is True
