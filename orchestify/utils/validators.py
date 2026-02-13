"""
Output validators for ABD artifacts.

Validates issue descriptions, pull requests, reviews, and scorecards.
"""

import re
from typing import List, Tuple

from orchestify.core.agent import Scorecard


class ValidationError(Exception):
    """Validation error."""
    pass


def validate_issue_format(content: str) -> Tuple[bool, List[str]]:
    """
    Validate issue description follows ABD template.

    Expected sections:
    - Title/Summary
    - Acceptance Criteria
    - Implementation Notes (optional)

    Args:
        content: Issue content

    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []

    if not content or not content.strip():
        errors.append("Issue content is empty")
        return False, errors

    # Check for required sections
    content_lower = content.lower()

    if "acceptance criteria" not in content_lower:
        errors.append("Missing 'Acceptance Criteria' section")

    # Check for reasonable length
    lines = content.strip().split("\n")
    if len(lines) < 3:
        errors.append("Issue description too brief (minimum 3 lines)")

    # Check for code block markers if implementation details present
    if "code" in content_lower or "implementation" in content_lower:
        if "```" not in content:
            errors.append("Code examples should be in markdown code blocks")

    # Check for proper formatting
    if not re.search(r"^#+\s+", content, re.MULTILINE):
        errors.append("Missing markdown headings")

    return len(errors) == 0, errors


def validate_pr_format(content: str) -> Tuple[bool, List[str]]:
    """
    Validate pull request description follows ABD template.

    Expected sections:
    - Description
    - Changes
    - Testing
    - Checklist

    Args:
        content: PR description

    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []

    if not content or not content.strip():
        errors.append("PR description is empty")
        return False, errors

    content_lower = content.lower()

    # Check for common PR sections
    has_description = "## description" in content_lower or "# description" in content_lower
    has_changes = "## changes" in content_lower or "# changes" in content_lower or \
                  "## what" in content_lower or "# what" in content_lower
    has_testing = "## testing" in content_lower or "# testing" in content_lower or \
                  "## test" in content_lower or "# test" in content_lower

    if not has_description:
        errors.append("Missing Description section")
    if not has_changes:
        errors.append("Missing Changes section")
    if not has_testing:
        errors.append("Missing Testing section")

    # Check for reasonable length
    lines = content.strip().split("\n")
    if len(lines) < 5:
        errors.append("PR description too brief")

    # Check for code references
    if not ("`" in content or "```" in content):
        errors.append("No code references or examples found")

    return len(errors) == 0, errors


def validate_review_format(content: str) -> Tuple[bool, List[str]]:
    """
    Validate code review follows ABD template.

    Expected elements:
    - Overall assessment
    - Specific comments (at least 1)
    - Suggestions/recommendations
    - Approval decision

    Args:
        content: Review content

    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []

    if not content or not content.strip():
        errors.append("Review content is empty")
        return False, errors

    content_lower = content.lower()

    # Check for assessment
    if not any(word in content_lower for word in ["looks good", "approve", "request", "change"]):
        errors.append("Missing clear assessment or approval decision")

    # Check for specific comments
    comment_indicators = ["function", "method", "line", "code", "variable", "issue"]
    has_comments = any(indicator in content_lower for indicator in comment_indicators)
    if not has_comments:
        errors.append("Missing specific code comments")

    # Check length
    lines = content.strip().split("\n")
    if len(lines) < 3:
        errors.append("Review too brief")

    # Check for actionable feedback
    if not any(verb in content_lower for verb in ["change", "fix", "update", "refactor", "improve"]):
        errors.append("Review lacks actionable feedback")

    return len(errors) == 0, errors


def validate_scorecard(scorecard: Scorecard) -> Tuple[bool, List[str]]:
    """
    Validate scorecard values and consistency.

    Args:
        scorecard: Scorecard to validate

    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []

    # Validate individual scores
    score_fields = [
        ("scope_control", scorecard.scope_control),
        ("behavior_fidelity", scorecard.behavior_fidelity),
        ("evidence_orientation", scorecard.evidence_orientation),
        ("actionability", scorecard.actionability),
        ("risk_awareness", scorecard.risk_awareness),
    ]

    for field_name, value in score_fields:
        if not isinstance(value, int):
            errors.append(f"{field_name} must be integer, got {type(value).__name__}")
        elif value < 0 or value > 2:
            errors.append(f"{field_name} must be 0-2, got {value}")

    # Validate total
    expected_total = (
        scorecard.scope_control
        + scorecard.behavior_fidelity
        + scorecard.evidence_orientation
        + scorecard.actionability
        + scorecard.risk_awareness
    )

    if scorecard.total != expected_total:
        errors.append(
            f"Total mismatch: expected {expected_total}, got {scorecard.total}"
        )

    # Validate interpretation
    valid_interpretations = {"promote", "patch", "anti-pattern"}
    if scorecard.interpretation.value not in valid_interpretations:
        errors.append(
            f"Invalid interpretation: {scorecard.interpretation.value}"
        )

    # Check interpretation matches total
    if scorecard.total >= 8:
        if scorecard.interpretation.value != "promote":
            errors.append(
                f"Score {scorecard.total} should interpret as 'promote'"
            )
    elif scorecard.total <= 3:
        if scorecard.interpretation.value != "anti-pattern":
            errors.append(
                f"Score {scorecard.total} should interpret as 'anti-pattern'"
            )
    else:
        if scorecard.interpretation.value != "patch":
            errors.append(
                f"Score {scorecard.total} should interpret as 'patch'"
            )

    return len(errors) == 0, errors


def validate_evidence(content: str, minimum_pieces: int = 1) -> Tuple[bool, List[str]]:
    """
    Validate that content contains sufficient evidence.

    Evidence indicators:
    - Code examples or snippets
    - Specific line numbers
    - Test results
    - Metrics or data
    - Quotes from output

    Args:
        content: Content to validate
        minimum_pieces: Minimum pieces of evidence required

    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []

    if not content or not content.strip():
        errors.append("Content is empty")
        return False, errors

    evidence_count = 0
    evidence_types = []

    # Code blocks
    if "```" in content:
        evidence_count += content.count("```") // 2
        evidence_types.append("code blocks")

    # Inline code
    if "`" in content:
        evidence_count += content.count("`") // 2
        evidence_types.append("inline code")

    # Line numbers
    if re.search(r"line\s+\d+", content, re.IGNORECASE):
        evidence_count += 1
        evidence_types.append("line numbers")

    # Test results
    if any(word in content.lower() for word in ["test", "passed", "failed", "error", "warning"]):
        evidence_count += 1
        evidence_types.append("test results")

    # Metrics
    if re.search(r"\d+\s*%|\d+\s*(ms|seconds|bytes)", content):
        evidence_count += 1
        evidence_types.append("metrics")

    # Output examples
    if ">" in content or re.search(r"\$\s+", content):
        evidence_count += 1
        evidence_types.append("command output")

    if evidence_count < minimum_pieces:
        errors.append(
            f"Insufficient evidence: found {evidence_count} pieces, "
            f"need minimum {minimum_pieces}. Found: {', '.join(evidence_types) if evidence_types else 'none'}"
        )

    return len(errors) == 0, errors


def validate_actionability(content: str) -> Tuple[bool, List[str]]:
    """
    Validate that content contains actionable items.

    Actionable language includes:
    - Imperative verbs (change, update, fix, add, remove, refactor, test)
    - Specific steps or procedures
    - Clear success criteria

    Args:
        content: Content to validate

    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []

    if not content or not content.strip():
        errors.append("Content is empty")
        return False, errors

    content_lower = content.lower()

    # Check for imperative verbs
    action_verbs = [
        "change", "update", "fix", "add", "remove", "refactor",
        "test", "implement", "create", "delete", "modify", "improve",
        "optimize", "replace", "configure", "enable", "disable"
    ]

    has_action_verb = any(verb in content_lower for verb in action_verbs)
    if not has_action_verb:
        errors.append("Missing action verbs (change, update, fix, etc.)")

    # Check for steps
    if re.search(r"step\s+\d+|^\d+\.", content, re.MULTILINE | re.IGNORECASE):
        pass  # Has numbered steps
    elif "-" in content or "*" in content:
        pass  # Has bullet points
    else:
        # Check for procedural language
        if not any(word in content_lower for word in ["then", "next", "after", "before"]):
            errors.append("Missing clear steps or procedures")

    # Check for success criteria
    if not any(phrase in content_lower for phrase in ["should", "must", "will", "expect"]):
        errors.append("Missing success criteria or expected outcomes")

    return len(errors) == 0, errors
