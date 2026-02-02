---
description: Execute a task using the Agent Behavior Development (ABD) paradigm
---

# ABD Task Workflow

This workflow guides you through the ABD lifecycle for a given task.

1.  **Analyze Request**: Read the user request and identify the behavior goal.
2.  **Load Skill**: Run `view_file .agent/skills/agent_behavior_development/SKILL.md` to load the ABD context.
3.  **Plan**:
    -   Create an implementation plan if the task is complex.
    -   Define the success criteria (Evidence).
4.  **Execute**:
    -   Implement the changes.
    -   **CRITICAL**: Do not just write code. Write the *verification logic* first if possible (TDD/BDD styles are welcome but Evidence is the goal).
    -   **MANDATORY**: Execute this step using the **Full Stack Engineering** skill rules (`.agent/skills/full_stack_engineering/SKILL.md`).
        -   Enforce SOLID, DRY, and encapuslation.
        -   Verify Architecture (Modular Monolith).
        -   Optimize for 100M+ scale.
5.  **Verify**:
    -   Run the evidence check.
    -   Self-evaluate using the `Scorecard` from the skill templates.
6.  **Report**:
    -   Present the evidence and the score to the user.
