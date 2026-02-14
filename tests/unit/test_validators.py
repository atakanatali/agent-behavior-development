"""Unit tests for orchestify.utils.validators module."""
import pytest

from orchestify.core.agent import Scorecard, Interpretation
from orchestify.utils.validators import (
    validate_actionability,
    validate_evidence,
    validate_issue_format,
    validate_pr_format,
    validate_review_format,
    validate_scorecard,
)


# ─── validate_issue_format Tests ───


class TestValidateIssueFormat:
    def test_valid_issue(self):
        content = """# Implement Auth

## Description
Build JWT authentication system.

## Acceptance Criteria
- Users can login
- Tokens expire after 1h
- Refresh tokens work
"""
        is_valid, errors = validate_issue_format(content)
        assert is_valid is True
        assert errors == []

    def test_empty_content(self):
        is_valid, errors = validate_issue_format("")
        assert is_valid is False
        assert "empty" in errors[0].lower()

    def test_missing_acceptance_criteria(self):
        content = """# Title
Some description here.
More details.
"""
        is_valid, errors = validate_issue_format(content)
        assert is_valid is False
        assert any("Acceptance Criteria" in e for e in errors)

    def test_too_brief(self):
        content = "# Title\nAcceptance Criteria"
        is_valid, errors = validate_issue_format(content)
        assert is_valid is False
        assert any("too brief" in e for e in errors)

    def test_code_without_blocks(self):
        content = """# Feature
Implementation details:
Add code to handle auth.
Some more lines.

## Acceptance Criteria
- Works
"""
        is_valid, errors = validate_issue_format(content)
        assert is_valid is False
        assert any("code blocks" in e.lower() for e in errors)

    def test_code_with_blocks(self):
        content = """# Feature
## Acceptance Criteria
- Works correctly

Implementation details:
```python
def auth(): pass
```
More details here.
"""
        is_valid, errors = validate_issue_format(content)
        assert is_valid is True

    def test_missing_headings(self):
        content = """No headings here
Just plain text
Acceptance criteria listed
More than three lines
"""
        is_valid, errors = validate_issue_format(content)
        assert any("headings" in e.lower() for e in errors)


# ─── validate_pr_format Tests ───


class TestValidatePrFormat:
    def test_valid_pr(self):
        content = """## Description
Added JWT authentication to the API.

## Changes
- Added `auth.py` with JWT handling
- Updated `middleware.py`

## Testing
```bash
pytest tests/test_auth.py
```
All tests pass.
Extra line for length.
"""
        is_valid, errors = validate_pr_format(content)
        assert is_valid is True

    def test_empty_pr(self):
        is_valid, errors = validate_pr_format("")
        assert is_valid is False

    def test_missing_description(self):
        content = """## Changes
- Added code

## Testing
- Tests pass
More content here.
Extra lines for length.
"""
        is_valid, errors = validate_pr_format(content)
        assert any("Description" in e for e in errors)

    def test_missing_testing(self):
        content = """## Description
Something was done.

## Changes
- Changed something
Extra content here.
More lines.
"""
        is_valid, errors = validate_pr_format(content)
        assert any("Testing" in e for e in errors)

    def test_too_brief(self):
        content = """## Description
Short
"""
        is_valid, errors = validate_pr_format(content)
        assert any("brief" in e.lower() for e in errors)


# ─── validate_review_format Tests ───


class TestValidateReviewFormat:
    def test_valid_review(self):
        content = """Looks good overall. I approve this change.

The function `authenticate()` handles token validation correctly.
Consider updating the error messages to be more descriptive.
Change the timeout from 30s to 60s.
"""
        is_valid, errors = validate_review_format(content)
        assert is_valid is True

    def test_empty_review(self):
        is_valid, errors = validate_review_format("")
        assert is_valid is False

    def test_missing_assessment(self):
        content = """The code runs fine.
Function works as expected.
No issues found with method calls.
"""
        is_valid, errors = validate_review_format(content)
        # Should find code comments but miss assessment
        assert any("assessment" in e.lower() for e in errors)

    def test_too_brief(self):
        content = "ok"
        is_valid, errors = validate_review_format(content)
        assert any("brief" in e.lower() for e in errors)


# ─── validate_scorecard Tests ───


class TestValidateScorecard:
    def test_valid_scorecard(self, sample_scorecard):
        is_valid, errors = validate_scorecard(sample_scorecard)
        assert is_valid is True
        assert errors == []

    def test_max_scorecard(self):
        sc = Scorecard(
            scope_control=2, behavior_fidelity=2,
            evidence_orientation=2, actionability=2, risk_awareness=2,
        )
        is_valid, errors = validate_scorecard(sc)
        assert is_valid is True

    def test_min_scorecard(self):
        sc = Scorecard(
            scope_control=0, behavior_fidelity=0,
            evidence_orientation=0, actionability=0, risk_awareness=0,
        )
        is_valid, errors = validate_scorecard(sc)
        assert is_valid is True

    def test_all_interpretations_correct(self):
        # Promote
        sc = Scorecard(
            scope_control=2, behavior_fidelity=2,
            evidence_orientation=2, actionability=2, risk_awareness=0,
        )
        is_valid, _ = validate_scorecard(sc)
        assert is_valid

        # Patch
        sc = Scorecard(
            scope_control=1, behavior_fidelity=1,
            evidence_orientation=1, actionability=1, risk_awareness=1,
        )
        is_valid, _ = validate_scorecard(sc)
        assert is_valid

        # Anti-pattern
        sc = Scorecard(
            scope_control=0, behavior_fidelity=0,
            evidence_orientation=0, actionability=0, risk_awareness=0,
        )
        is_valid, _ = validate_scorecard(sc)
        assert is_valid


# ─── validate_evidence Tests ───


class TestValidateEvidence:
    def test_code_block_evidence(self):
        content = "Here is evidence:\n```python\ndef test(): pass\n```"
        is_valid, errors = validate_evidence(content)
        assert is_valid is True

    def test_inline_code_evidence(self):
        content = "The variable `user_id` should be validated"
        is_valid, errors = validate_evidence(content)
        assert is_valid is True

    def test_line_number_evidence(self):
        content = "Error found at line 42 in the auth module"
        is_valid, errors = validate_evidence(content)
        assert is_valid is True

    def test_test_result_evidence(self):
        content = "All tests passed successfully with 0 failures"
        is_valid, errors = validate_evidence(content)
        assert is_valid is True

    def test_metrics_evidence(self):
        content = "Response time improved to 50ms average"
        is_valid, errors = validate_evidence(content)
        assert is_valid is True

    def test_no_evidence(self):
        content = "Everything looks fine and works well."
        is_valid, errors = validate_evidence(content)
        assert is_valid is False
        assert any("Insufficient evidence" in e for e in errors)

    def test_empty_content(self):
        is_valid, errors = validate_evidence("")
        assert is_valid is False

    def test_minimum_pieces(self):
        content = "Test passed with `auth_module` at line 10"
        is_valid, errors = validate_evidence(content, minimum_pieces=3)
        assert is_valid is True  # Has inline code, test result, and line number

    def test_high_minimum_fails(self):
        content = "Just a single `code` reference"
        is_valid, errors = validate_evidence(content, minimum_pieces=10)
        assert is_valid is False


# ─── validate_actionability Tests ───


class TestValidateActionability:
    def test_actionable_content(self):
        content = """1. Change the auth handler to use JWT
2. Update the middleware configuration
The function should return a valid token.
"""
        is_valid, errors = validate_actionability(content)
        assert is_valid is True

    def test_empty_content(self):
        is_valid, errors = validate_actionability("")
        assert is_valid is False

    def test_missing_action_verbs(self):
        content = "The system is good and works well. It should be fine."
        is_valid, errors = validate_actionability(content)
        assert any("action verbs" in e.lower() for e in errors)

    def test_with_bullet_points(self):
        content = """- Fix the authentication bug
- The login should work properly
"""
        is_valid, errors = validate_actionability(content)
        assert is_valid is True

    def test_with_numbered_steps(self):
        content = """Step 1: Create the auth module
Step 2: Add middleware
The system must handle tokens correctly.
"""
        is_valid, errors = validate_actionability(content)
        assert is_valid is True

    def test_missing_success_criteria(self):
        content = """- Fix the bug
- Update the code
Then deploy the changes.
"""
        is_valid, errors = validate_actionability(content)
        assert any("success criteria" in e.lower() for e in errors)
