# Self-Fix Policy

Self-fix is the agent's ability to debug and correct its own output
before entering the recycle loop with other agents.

## Definition

Self-fix occurs when an agent:
- produces code that fails build, lint, or tests
- detects the failure through automated checks
- analyzes the error output
- generates a corrective fix
- retries the checks

This is distinct from recycle.

## Self-Fix vs Recycle

Self-fix:
- agent corrects its OWN errors
- triggered by automated tool output (compiler, linter, test runner)
- no other agent is involved
- happens BEFORE PR is opened

Recycle:
- agent receives feedback from ANOTHER agent (reviewer, QA)
- triggered by behavioral or structural issues
- requires inter-agent communication
- happens AFTER PR is opened

## Self-Fix Limits

Default maximum self-fix attempts: 5

This limit is configurable per project.

If the agent exceeds the self-fix limit:
1. Stop all fix attempts
2. Log the full error history
3. Report to the orchestrator
4. Enter escalation mode (notify user)

## Self-Fix Logging

Each self-fix attempt must record:
- attempt number
- error type (build, lint, test)
- error message (captured from tool output)
- fix description (what the agent changed)
- result (pass or fail)

## Self-Fix Quality Rules

An agent must NOT:
- apply the same fix twice
- ignore an error and proceed
- delete tests to make them pass
- disable linting rules to avoid errors
- reduce code coverage to pass checks

An agent MUST:
- read the full error output before attempting a fix
- explain its analysis before applying a fix
- track which files were modified in each attempt
- preserve all previous working code

## Escalation

When self-fix limit is reached:
- the agent produces a self-fix report
- the report includes all attempts and their outcomes
- the orchestrator decides: retry with different approach or notify user
- the user may adjust the prompt, guardrails, or self-fix limit

## Configuring Self-Fix

In project configuration:
```yaml
dev_loop:
  max_self_fix: 5
  build_cmd: "npm run build"
  lint_cmd: "npm run lint"
  test_cmd: "npm test"
  timeout_per_command: 120  # seconds
```

The self-fix limit can be adjusted per project complexity.
Simple projects may need only 3 attempts.
Complex projects may allow up to 7.

More than 7 self-fix attempts indicates a prompt or specification defect,
not a code defect. Fix the prompt first.
