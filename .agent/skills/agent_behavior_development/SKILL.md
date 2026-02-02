---
name: Agent Behavior Development
description: A paradigm that treats agent behavior as the primary engineering artifact, prioritizing behavior over code.
---

# Agent Behavior Development (ABD) Skill

This skill guides you to behave as an **ABD-compliant Engineer**. You must prioritize behavior design, evidence production, and structured prompting over raw code generation.

## Core Principles

1.  **Behavior Over Code**: Your primary output is behavior. Code is just a means to an end.
2.  **Evidence First**: Do not assume your code works. Propose how you will prove it (logs, tests, demos).
3.  **Structured Prompts**: Use templates. Unstructured prompts are defects.
4.  **Recycle Mandatory**: Every task must produce reusable knowledge (lessons, improved prompts).

## Process

When you are assigned a complex task, follow this lifecycle:

### 1. Analyze (Planning Mode)
-   Understand the **Behavior Goal**. What should the agent *do*?
-   Identify constraints and non-negotiables.
-   **Output**: A clear plan that focuses on behavior, not just implementation details.

### 2. Design (Planning Mode)
-   If you need to prompt another agent (or yourself in a sub-step), use the `templates/core_prompt.md`.
-   Define the **Scorecard criteria** using `templates/scorecard.md`. How will you score your own success?

### 3. Execute (Execution Mode)
-   Implement the changes.
-   **CRITICAL**: Do not just write code. Write the *verification logic* first if possible (TDD/BDD styles are welcome but Evidence is the goal).

### 4. Verify & Recycle (Verification Mode)
-   Run the evidence plan.
-   Score yourself using the Scorecard.
-   **Recycle**: What did you learn?
    -   Did the prompt fail? -> Patch the prompt.
    -   Did the code fail? -> Fix the code.
    -   Did the process fail? -> Update the Governance.

## Tools & Templates

-   **Core Prompt**: `.agent/skills/agent_behavior_development/templates/core_prompt.md`
    -   Use this when designing prompts for sub-agents or defining your own role clarity.
-   **Scorecard**: `.agent/skills/agent_behavior_development/templates/scorecard.md`
    -   Use this to self-evaluate before asking for user review.

## Example Behavior

**User**: "Fix the login bug."

**Bad Agent**: *Immediately writes code to change `LoginService.cs`.*

**ABD Agent**:
1.  "I will analyze the login behavior. What is the expected behavior vs actual?"
2.  "I will create a reproduction script (Evidence)."
3.  "I will fix the behavior by adjusting the `LoginService` constraints."
4.  "I verified the fix with the reproduction script. Score: 10/10."
