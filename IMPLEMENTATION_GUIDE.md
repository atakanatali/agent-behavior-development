# ABD Orchestration Engine - Implementation Guide

## Overview

The ABD (Agent Behavior Development) Orchestration Engine is a production-grade framework for managing multi-agent workflows with state persistence, output validation, and comprehensive logging.

**Created Files:**
- 7 Python modules totaling 2,454 lines of code
- Full type hints and docstrings throughout
- Production-quality error handling and logging
- Thread-safe state management

## Architecture

```
ABD Pipeline: TPM → Architect → [Issue Loop] → Complete

┌─────────────────────────────────────────────────────────────┐
│ OrchestrifyEngine (Orchestrator)                             │
├─────────────────────────────────────────────────────────────┤
│ Phase 1: TPM Agent          → Generate epic plan             │
│ Phase 2: Architect Agent    → Design architecture            │
│ Phase 3: Issue Loop         → Process each issue             │
│   ├─ Engineer Agent         → Implement solution             │
│   ├─ Reviewer Agent         → Code review (up to 3 cycles)   │
│   ├─ QA Agent               → Testing (up to 3 cycles)       │
│   └─ Architect Agent        → Final review & merge           │
│ Phase 4: Complete           → Finalize epic                  │
└─────────────────────────────────────────────────────────────┘

StateManager (Persistence Layer)
├─ .orchestify/state.json      [Epic & issue state]
├─ .orchestify/logs/           [Structured logs]
└─ Thread-safe RLock access    [Atomic updates]
```

## File Descriptions

### Core Modules (orchestify/core/)

#### state.py (379 lines)
State persistence module with thread-safe access and automatic JSON serialization.

**Key Classes:**
- `IssueStatus`: pending, in_progress, review, qa, done, escalated
- `EpicStatus`: pending, in_progress, complete, failed
- `CycleState`: Records workflow transitions with timestamps
- `IssueState`: Tracks issue metadata, PR info, cycle counts, scorecard
- `EpicState`: Container for related issues with status
- `StateManager`: Main API for state management

**Key Methods:**
```python
StateManager(repo_root: Path)
  .load() -> Dict[epic_id, EpicState]
  .create_epic(epic_id) -> EpicState
  .update_issue(epic_id, issue_number, data) -> IssueState
  .add_cycle(epic_id, issue_number, agent_from, agent_to, action, result) -> CycleState
  .get_next_issue(epic_id) -> Optional[IssueState]
  .is_epic_complete(epic_id) -> bool
  .update_epic_status(epic_id, status) -> EpicState
```

**Thread Safety:** All methods use `threading.RLock()` for atomic operations.

**Persistence:** Changes immediately written to `.orchestify/state.json` with proper JSON serialization.

#### agent.py (369 lines)
Base agent class and data models for the ABD framework.

**Key Data Classes:**
- `AgentContext`: Execution context with goal, instructions, behavior spec, dependencies
- `AgentResult`: Output, files changed, commands run, token count, duration
- `Scorecard`: ABD evaluation with 5 dimensions (scope_control, behavior_fidelity, evidence_orientation, actionability, risk_awareness)
- `RecycleOutput`: Strategy for reusing/banning agent approaches

**Base Class:**
```python
class BaseAgent(ABC):
  __init__(agent_id, config, provider, memory_client=None)
  async execute(context: AgentContext) -> AgentResult
  score(result: AgentResult) -> Scorecard
  recycle(result: AgentResult, scorecard: Scorecard) -> RecycleOutput
  
  _load_persona() -> str
  _load_guardrails() -> str
  _build_messages(context: AgentContext) -> List[dict]
  _validate_output(output: str) -> bool
  async _call_llm(messages, temperature, max_tokens) -> (str, int)
```

**Scorecard System:**
- Each dimension scored 0-2
- Auto-calculates total (max 10)
- Auto-interprets: promote (8+), patch (4-7), anti-pattern (<=3)

#### engine.py (554 lines)
Main orchestration engine managing the full ABD pipeline.

**Key Methods:**
```python
class OrchestrifyEngine:
  __init__(config, state_manager, provider_registry, memory_client)
  register_agent(agent_id, agent) -> None
  
  # Pipeline phases
  async run_full_pipeline(plan_file, prompt) -> Dict
  async run_phase(phase, **kwargs) -> Dict
  async _run_tpm(input_text) -> Dict
  async _run_architect(epic_id) -> Dict
  async _run_issue_loop(epic_id) -> Dict
  async _run_issue_cycle(epic_id, issue_number) -> Dict
  async _run_engineer(epic_id, issue_number) -> Dict
  async _run_reviewer(epic_id, issue_number, pr_number) -> Dict
  async _run_qa(epic_id, issue_number, pr_number) -> Dict
  async _run_architect_final(epic_id, issue_number, pr_number) -> Dict
  async _run_complete(epic_id) -> Dict
  
  # Utility
  async _escalate(epic_id, issue_number, reason) -> None
  async _notify_user(message) -> None
```

**Features:**
- Full state tracking across phases
- Automatic escalation on failures
- Recycle limit enforcement (3 max for review, 3 max for QA)
- Error recovery and logging
- Resume capability from saved state

### Utility Modules (orchestify/utils/)

#### logger.py (111 lines)
Structured logging with Rich console formatting.

**Functions:**
```python
get_logger(name: str) -> logging.Logger
get_file_logger(name: str, log_file: Optional[Path]) -> logging.Logger
```

**Features:**
- File logging to `.orchestify/logs/orchestify.log`
- Rich console formatting (colors, tracebacks)
- Global logger cache to avoid duplicates
- Format: `[timestamp] [name] [level] message`

#### retry.py (318 lines)
Retry decorators with exponential backoff.

**Decorators:**
```python
@retry_llm_call(max_retries=3, initial_wait=1, max_wait=32)
@retry_github_call(max_retries=3, initial_wait=2, max_wait=60)
@with_retries(max_retries=3, backoff=1.5, on_retry=None)
```

**Features:**
- Detects rate limits, timeouts, connection errors
- Exponential backoff with configurable bounds
- Supports both sync and async
- Graceful fallback if tenacity not installed
- Optional retry callbacks

#### validators.py (340 lines)
Output validation for ABD artifacts.

**Functions:**
```python
validate_issue_format(content: str) -> (bool, [errors])
validate_pr_format(content: str) -> (bool, [errors])
validate_review_format(content: str) -> (bool, [errors])
validate_scorecard(scorecard: Scorecard) -> (bool, [errors])
validate_evidence(content: str, minimum_pieces=1) -> (bool, [errors])
validate_actionability(content: str) -> (bool, [errors])
```

**Features:**
- Template compliance checking
- Evidence detection (code, tests, metrics, output)
- Action verb detection
- Scorecard consistency validation
- Detailed error messages

## Usage Patterns

### 1. Initialize and Run Pipeline
```python
from orchestify.core import StateManager, OrchestrifyEngine
from pathlib import Path

# Setup
state_manager = StateManager(Path("/path/to/repo"))
engine = OrchestrifyEngine(
    config={"max_self_fixes": 3},
    state_manager=state_manager,
    provider_registry={"openai": provider},
)

# Register agents
engine.register_agent("tpm", tpm_agent)
engine.register_agent("architect", architect_agent)
engine.register_agent("engineer", engineer_agent)
engine.register_agent("reviewer", reviewer_agent)
engine.register_agent("qa", qa_agent)

# Run
result = await engine.run_full_pipeline(prompt="Your task")
```

### 2. Implement Custom Agent
```python
from orchestify.core import BaseAgent, AgentContext, AgentResult, Scorecard

class CustomAgent(BaseAgent):
    async def execute(self, context: AgentContext) -> AgentResult:
        messages = self._build_messages(context)
        output, tokens = await self._call_llm(messages)
        return AgentResult(output=output, tokens_used=tokens)
    
    def score(self, result: AgentResult) -> Scorecard:
        # Evaluate based on ABD criteria
        return Scorecard(
            scope_control=2,
            behavior_fidelity=2,
            evidence_orientation=1,
            actionability=2,
            risk_awareness=1
        )
```

### 3. Resume from State
```python
state = state_manager.load()
for epic_id, epic in state.items():
    if epic.status == EpicStatus.IN_PROGRESS:
        # Resume processing
        next_issue = state_manager.get_next_issue(epic_id)
        if next_issue:
            result = await engine._run_issue_cycle(epic_id, next_issue.issue_number)
```

### 4. Validate Output
```python
from orchestify.utils.validators import validate_evidence, validate_scorecard

# Check evidence
is_valid, errors = validate_evidence(output, minimum_pieces=2)

# Check scorecard
is_valid, errors = validate_scorecard(scorecard)

if not is_valid:
    print("Validation errors:", errors)
```

## Configuration

### StateManager
- `repo_root`: Path to target repository
- State file: `.orchestify/state.json`
- Log directory: `.orchestify/logs/`

### OrchestrifyEngine
- `config` dict with options:
  - `max_retries`: LLM call retries (default: 3)
  - `max_self_fixes`: Engineer self-fix attempts (default: 3)
  - `max_tokens`: LLM response limit (default: 4096)
  - Review cycles: max 3 per issue
  - QA cycles: max 3 per issue

### Agent Base Class
- `agent_id`: Unique identifier
- `config`: Agent-specific configuration
- `provider`: LLM provider instance
- `memory_client`: Optional memory/context client
- Personas: loaded from `prompts/personas/{agent_id}.md`
- Guardrails: loaded from `prompts/guardrails.md`

## Error Handling

### Automatic Retry
- LLM calls retry on rate limits and timeouts
- GitHub API calls retry with longer backoff
- Configurable max retries and backoff parameters

### Escalation
- Issues automatically escalated on repeated failures
- Max 3 review cycles enforced
- Max 3 QA cycles enforced
- User notified of escalations

### Logging
- All operations logged with context
- File and console handlers
- Rich formatting for readability
- Debug logs to file, info+ to console

## State Persistence

### Automatic Saving
- All state changes trigger disk write
- Atomic writes with file locking
- JSON format for easy inspection
- ISO8601 timestamps for all events

### State Structure
```json
{
  "epic-001": {
    "epic_id": "epic-001",
    "status": "in_progress",
    "issues": [
      {
        "issue_number": 42,
        "status": "in_progress",
        "pr_number": 123,
        "review_cycles": 1,
        "qa_cycles": 0,
        "scorecard": {...},
        "cycle_history": [
          {
            "cycle_number": 1,
            "agent_from": "engineer",
            "agent_to": "reviewer",
            "action": "...",
            "result": "...",
            "timestamp": "2024-02-13T..."
          }
        ]
      }
    ],
    "created_at": "2024-02-13T...",
    "updated_at": "2024-02-13T..."
  }
}
```

## Type System

### Enums
- `IssueStatus`: pending, in_progress, review, qa, done, escalated
- `EpicStatus`: pending, in_progress, complete, failed
- `Interpretation`: promote, patch, anti-pattern

### Data Classes
All data classes have:
- Type-safe fields with defaults
- `to_dict()` method for serialization
- `from_dict()` classmethod for deserialization
- Proper `__post_init__` validation

## Testing Integration

### Validation Framework
```python
# Test output quality
is_valid, errors = validate_issue_format(issue_text)
assert is_valid, f"Invalid: {errors}"

# Test scorecard
scorecard = Scorecard(...)
is_valid, errors = validate_scorecard(scorecard)
assert is_valid

# Test evidence
is_evidenced, errors = validate_evidence(output, minimum_pieces=3)
assert is_evidenced

# Test actionability
is_actionable, errors = validate_actionability(output)
assert is_actionable
```

## Performance Characteristics

- State loads from JSON on first access (subsequent loads cached)
- State saves trigger disk write (non-blocking in async context)
- Scorecard calculations O(1)
- Validation checks O(n) where n = content length
- Retry backoff: exponential (1s, 2s, 4s, ...)

## Future Extensions

The framework supports:
1. Custom validators (inherit and extend)
2. Custom agents (inherit BaseAgent)
3. Custom providers (implement call interface)
4. Custom memory backends (implement context interface)
5. Additional logging handlers (via logger module)
6. Custom retry strategies (via retry decorators)

## Dependencies

Required:
- Python 3.8+
- asyncio (standard library)
- dataclasses (standard library)
- json (standard library)
- threading (standard library)
- logging (standard library)
- pathlib (standard library)

Optional:
- tenacity (for advanced retry handling)
- rich (for console formatting)

## Files Created

```
/sessions/cool-brave-lovelace/mnt/agent-behavior-development/orchestify/
├── __init__.py
├── core/
│   ├── __init__.py                    (35 lines)
│   ├── state.py                       (379 lines)
│   ├── agent.py                       (369 lines)
│   └── engine.py                      (554 lines)
└── utils/
    ├── __init__.py                    (1 line)
    ├── logger.py                      (111 lines)
    ├── retry.py                       (318 lines)
    └── validators.py                  (340 lines)

Documentation:
├── MANIFEST.md                        (Quick reference)
├── CODE_EXAMPLES.md                   (Usage patterns)
└── IMPLEMENTATION_GUIDE.md            (This file)
```

## Getting Started Checklist

1. Create agent implementations inheriting `BaseAgent`
2. Create `prompts/personas/{agent_id}.md` for each agent
3. Create `prompts/guardrails.md` (shared guardrails)
4. Initialize `StateManager` with repo path
5. Initialize `OrchestrifyEngine` with config
6. Register all agents with engine
7. Call `await engine.run_full_pipeline(prompt="your task")`
8. Monitor `.orchestify/state.json` for progress
9. Check `.orchestify/logs/orchestify.log` for debug info
10. Implement custom `score()` and `recycle()` in agents as needed

