# Orchestify — Agent Behavior Development (ABD) Engine

Multi-agent orchestration engine for software development using the **behavior-over-code** paradigm.

## What is ABD?

Agent Behavior Development (ABD) shifts the focus from writing code to defining behaviors. Instead of coding line by line, you describe *what* agents should do — and the orchestration engine handles the *how*.

The ABD manifesto emphasizes behavior fidelity, scope control, evidence-based decisions, and continuous recycling of knowledge through a scorecard system.

## Quick Start

```bash
# Install
pip install agent-behavior-development

# Global setup (one-time)
orchestify install

# Initialize a sprint in your git repo
cd your-project
orchestify init -p "Build user authentication with JWT"

# Plan with TPM agent
orchestify plan

# Run the pipeline
orchestify start

# Check progress
orchestify status
orchestify inspect
```

## Architecture

Orchestify runs a multi-phase pipeline for each sprint:

```
TPM → Architect → Engineer → Reviewer → QA → Complete
```

Each phase is handled by a specialized agent with defined behavior specs. The scorecard system evaluates agent output across five dimensions: scope control, behavior fidelity, evidence orientation, actionability, and risk awareness.

### Sprint-Based Sessions

Each execution runs inside an isolated sprint context stored in `.orchestify/<sprint_id>/`. Multiple sprints can run in parallel from different terminals.

```
.orchestify/
├── swift-core-4821/         # Sprint 1
│   ├── config.yaml
│   ├── state.json
│   ├── logs/
│   │   ├── tpm.log
│   │   ├── engineer.log
│   │   └── engineer_task.yaml
│   ├── artifacts/
│   ├── personas/
│   ├── rules/
│   └── prompts/
└── bold-apex-1337/          # Sprint 2 (parallel)
    └── ...
```

## CLI Commands

| Command | Description |
|---------|------------|
| `orchestify` | Show welcome screen |
| `orchestify install` | Global setup wizard |
| `orchestify init` | Initialize sprint in git repo |
| `orchestify plan` | Interactive TPM planning session |
| `orchestify start` | Run orchestration pipeline |
| `orchestify status` | View sprint status |
| `orchestify inspect` | View agent activity/logs |
| `orchestify memory` | Manage Contextify memory |
| `orchestify config` | Configuration management |
| `orchestify stop` | Pause running sprint |
| `orchestify resume` | Resume paused sprint |

## Configuration

Three-tier configuration hierarchy:

1. **Global** (`~/.config/orchestify/global.yaml`) — User preferences, API keys, defaults
2. **Project** (`config/`) — Project-specific settings, agent configs, provider setup
3. **Sprint** (`.orchestify/<sprint_id>/config.yaml`) — Sprint-level overrides

### Agent Configuration

```yaml
# config/agents.yaml
agents:
  tpm:
    provider: anthropic
    model: claude-opus-4-6
    temperature: 0.7
    thinking: true
    mode: interactive
  engineer:
    provider: anthropic
    model: claude-opus-4-6
    temperature: 0.5
    mode: autonomous
```

### Provider Configuration

```yaml
# config/providers.yaml
providers:
  anthropic:
    type: anthropic
    api_key: ${ANTHROPIC_API_KEY}
    default_model: claude-opus-4-6
```

## Agent Roles

Orchestify includes 11 specialized agent roles:

- **TPM (Task Planning Model)** — Breaks goals into epics and issues
- **Architect** — Designs system architecture and technical approach
- **Engineer** — Implements code changes with self-fix loop
- **Reviewer** — Reviews code quality and behavior compliance
- **QA** — Validates through testing and integration checks
- **Validator** — Schema and contract validation
- **Debugger** — Root cause analysis
- **Documenter** — Documentation generation
- **Synthesizer** — Cross-agent knowledge synthesis
- **Scorecardist** — Evaluates agent output quality
- **Recycler** — Extracts reusable patterns from completed work

## Scorecard System

Every agent output is scored across five dimensions (0-2 each):

| Dimension | 0 | 1 | 2 |
|-----------|---|---|---|
| Scope Control | Off-scope | Partial | On-scope |
| Behavior Fidelity | Deviated | Partial | Faithful |
| Evidence Orientation | No evidence | Some evidence | Well-evidenced |
| Actionability | Vague | Partial | Actionable |
| Risk Awareness | Ignored | Acknowledged | Mitigated |

**Interpretation**: 8-10 = Promote, 5-7 = Recycle, 0-4 = Anti-pattern

## Memory Integration

Orchestify supports Contextify for persistent agent memory across three layers:

- **Agent layer** — Individual agent context
- **Epic layer** — Shared within an epic
- **Global layer** — Cross-project knowledge

Fallback to local JSON storage when Contextify is not available.

## Development

```bash
# Clone
git clone https://github.com/atakanatali/agent-behavior-development.git
cd agent-behavior-development

# Install dev dependencies
pip install -e ".[dev]" --break-system-packages

# Run tests
pytest

# Run with coverage
pytest --cov=orchestify --cov-report=term-missing
```

## Requirements

- Python 3.11+
- Git repository (for `orchestify init`)
- GitHub CLI (`gh`) — optional, for PR management
- LLM API key (Anthropic, OpenAI, or LiteLLM compatible)

## License

MIT

## Author

Atakan Atali (atakanatali6@gmail.com)
