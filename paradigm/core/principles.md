# Core Principles of Agent Behavior Development

Agent Behavior Development (ABD) is built on a small set of strict principles.
These principles are non-negotiable and define the paradigm.

## Principle 1: Behavior Over Code

In ABD, behavior is more important than code.

Code is a result.
Behavior is the system that produces results.

If output quality is poor, the first response is NOT to rewrite code.
The first response is to inspect and improve agent behavior.

## Principle 2: Prompts Are Engineering Artifacts

Prompts are not messages.
Prompts are not instructions written casually.

Prompts are engineered artifacts that:
- have structure
- have constraints
- have versions
- are reviewed
- are patched
- are promoted

A prompt without structure is a defect.

## Principle 3: Evidence Before Acceptance

ABD does not require tests specifically.
ABD requires evidence.

Evidence proves behavior.
Evidence can be:
- tests
- checks
- demos
- measurements

Behavior without evidence is invalid.

## Principle 4: Humans Design, Agents Produce

Agents do not make decisions.
Agents produce options and drafts under rules.

Humans:
- define boundaries
- approve tradeoffs
- accept risk

Agents:
- generate structured output
- follow constraints
- stop on uncertainty

## Principle 5: Recycle Is Mandatory

Every task must improve the future.

If a task does not produce reusable knowledge,
the task is incomplete.

Recycle output is required:
- Kept
- Reused
- Banned

## Principle 6: Failures Are Fixed at the Behavior Level

When failures occur:
1. Fix prompt structure
2. Tighten guardrails
3. Lock output format
4. Improve review rules
5. Update recycle rules

Only after these steps is code changed.
