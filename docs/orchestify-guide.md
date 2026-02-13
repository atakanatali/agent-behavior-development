# Orchestify User Guide

Complete guide for using Orchestify — the ABD multi-agent orchestration engine.

## Table of Contents

1. [Installation](#installation)
2. [First Sprint](#first-sprint)
3. [CLI Reference](#cli-reference)
4. [Configuration](#configuration)
5. [Sprint Management](#sprint-management)
6. [Agent System](#agent-system)
7. [Scorecard & Recycle](#scorecard--recycle)
8. [Memory System](#memory-system)
9. [Troubleshooting](#troubleshooting)

---

## Installation

### Via pip

```bash
pip install agent-behavior-development
```

### Via pipx (recommended for CLI tools)

```bash
pipx install agent-behavior-development
```

### From source

```bash
git clone https://github.com/atakanatali/agent-behavior-development.git
cd agent-behavior-development
pip install -e ".[dev]"
```

### Global Setup

After installation, run the install wizard:

```bash
orchestify install
```

This creates `~/.config/orchestify/global.yaml` with your preferences, API keys, and defaults.

---

## First Sprint

### 1. Initialize

Navigate to your git repository and create a sprint:

```bash
cd my-project
orchestify init -p "Build a REST API with authentication"
```

This creates:
- `config/` directory with project configuration files
- `.orchestify/<sprint-id>/` directory for the sprint

### 2. Plan

Start an interactive planning session with the TPM agent:

```bash
orchestify plan
```

The TPM agent will analyze your goal and create an epic with actionable issues.

### 3. Execute

Run the full pipeline:

```bash
orchestify start
```

The pipeline executes: TPM → Architect → Engineer Loop → Review → QA → Complete

### 4. Monitor

Check progress at any time:

```bash
# Sprint status
orchestify status

# Agent activity
orchestify inspect

# Specific agent logs
orchestify inspect --agent engineer

# Activity timeline
orchestify inspect --timeline
```

---

## CLI Reference

### orchestify (no args)

Shows the welcome screen with quick-start commands.

### orchestify install

```bash
orchestify install [--force]
```

Interactive setup wizard for global configuration. Use `--force` to reconfigure.

### orchestify init

```bash
orchestify init [--name NAME] [--prompt TEXT] [--no-git-check]
```

Initialize a new sprint in the current git repository.

Options:
- `--name` — Custom sprint ID (auto-generated if omitted)
- `--prompt, -p` — Initial goal/prompt for the sprint
- `--no-git-check` — Skip git repository validation

### orchestify plan

```bash
orchestify plan [--sprint ID] [--prompt TEXT] [--non-interactive]
```

Start an interactive TPM planning session.

### orchestify start

```bash
orchestify start [--sprint ID] [--phase PHASE] [--issue NUM] [--dry-run]
```

Run the orchestration pipeline.

Options:
- `--sprint, -s` — Target sprint (default: latest)
- `--phase` — Start from specific phase (tpm/architect/engineer/reviewer/qa)
- `--issue` — Run specific issue only
- `--dry-run` — Simulate without making changes

### orchestify status

```bash
orchestify status [--sprint ID] [--all]
```

View sprint and pipeline status.

### orchestify inspect

```bash
orchestify inspect [--sprint ID] [--agent ID] [--limit N] [--level LEVEL] [--timeline] [--task]
```

View agent activity, logs, and task checkpoints.

### orchestify memory

```bash
orchestify memory status       # Check memory backend
orchestify memory start        # Enable Contextify
orchestify memory stop         # Disable memory
orchestify memory query        # Query stored entries
orchestify memory clear        # Clear all memory
```

### orchestify config

```bash
orchestify config validate     # Validate config files
orchestify config show         # Display current config
orchestify config show --global # Show global config
```

### orchestify stop

```bash
orchestify stop [--sprint ID] [--force]
```

Pause a running sprint. State is preserved for later resumption.

### orchestify resume

```bash
orchestify resume [--sprint ID]
```

Resume a paused sprint from its last checkpoint.

---

## Configuration

### Hierarchy

1. **Global** (`~/.config/orchestify/global.yaml`)
   - User info, API keys, default provider/model, preferences

2. **Project** (`config/`)
   - `orchestify.yaml` — Project settings, orchestration rules
   - `agents.yaml` — Agent configurations
   - `providers.yaml` — LLM provider setup
   - `memory.yaml` — Memory/Contextify settings

3. **Sprint** (`.orchestify/<sprint_id>/config.yaml`)
   - Per-sprint overrides

### Environment Variables

API keys can be set via environment variables:

```bash
export ANTHROPIC_API_KEY=sk-...
export OPENAI_API_KEY=sk-...
```

---

## Sprint Management

### Readable Sprint IDs

Sprints get readable IDs like `swift-core-4821` or `bold-apex-1337` instead of UUIDs.

### Parallel Sprints

Multiple sprints can run simultaneously from different terminals:

```bash
# Terminal 1
orchestify init -p "Feature A"
orchestify start

# Terminal 2
orchestify init -p "Feature B"
orchestify start
```

### Sprint Directory Structure

```
.orchestify/<sprint-id>/
├── config.yaml          # Sprint-level config overrides
├── state.json           # Sprint state (status, progress, PID)
├── logs/                # Agent execution logs
│   ├── tpm.log          # Append-only timestamped log
│   ├── engineer.log
│   ├── engineer_task.yaml  # Task checkpoint for resume
│   └── ...
├── artifacts/           # Generated artifacts (plans, reports)
├── personas/            # Agent persona definitions
├── rules/               # Behavior rules
└── prompts/             # Custom prompts
```

### Sprint Lifecycle

```
created → planned → running → complete
                  ↓          ↗
                paused ──────
                  ↓
                error
```

---

## Agent System

### Pipeline Flow

```
TPM → Architect → [Engineer → Reviewer → QA]* → Complete
                   └── Issue Loop (repeat per issue) ──┘
```

### Self-Fix Loop

The Engineer agent has a built-in self-fix loop:
1. Implement changes
2. Run build/lint/test commands
3. If failures: fix and retry (up to `max_self_fix` times)
4. If still failing: escalate

### Escalation

Issues that exceed max review or QA cycles are escalated to the user with context about what was attempted and why it failed.

---

## Scorecard & Recycle

### Scoring

Every agent output is scored on five dimensions (0-2 each, max total = 10):

- **Scope Control** — Did the agent stay within scope?
- **Behavior Fidelity** — Did it follow the behavior spec?
- **Evidence Orientation** — Are claims supported by evidence?
- **Actionability** — Can the output be acted upon directly?
- **Risk Awareness** — Were risks identified and mitigated?

### Interpretation

| Total Score | Interpretation | Action |
|------------|----------------|--------|
| 8-10 | Promote | Advance to next phase |
| 5-7 | Recycle | Re-run with feedback |
| 0-4 | Anti-pattern | Escalate or abandon |

### Recycling

When output is recycled, the Recycler agent extracts:
- **Kept** — Patterns worth preserving
- **Reused** — Patterns from previous cycles
- **Banned** — Anti-patterns to avoid

---

## Memory System

### Layers

- **Agent** — Context specific to one agent (e.g., engineer's learned patterns)
- **Epic** — Shared context within an epic (e.g., architecture decisions)
- **Global** — Cross-project knowledge (e.g., code conventions)

### Backends

- **Local** — JSON files in `.orchestify/memory/` (default)
- **Contextify** — HTTP-based memory service for production use

---

## Troubleshooting

### "Not a git repository"

Run `orchestify init` from within a git repo, or use `--no-git-check`.

### "Config directory not found"

Run `orchestify init` to create the config directory.

### "TPM agent not configured"

Ensure `config/agents.yaml` has a `tpm` agent entry and your API key is set.

### Sprint stuck in "running"

The sprint's process may have crashed. Use `orchestify stop --force` to reset it, then `orchestify resume`.

### API key not found

Set via environment variable or `orchestify install`:
```bash
export ANTHROPIC_API_KEY=sk-...
```
