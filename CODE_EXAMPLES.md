# ABD Orchestration Engine - Code Examples

## 1. State Management

### Creating and Managing Epic State
```python
from orchestify.core import StateManager, IssueStatus
from pathlib import Path

# Initialize state manager
state_manager = StateManager(Path("/path/to/repo"))

# Create or get epic
epic = state_manager.create_epic("epic-001")
print(f"Epic created: {epic.epic_id}, status: {epic.status}")

# Update issue in epic
issue = state_manager.update_issue(
    epic_id="epic-001",
    issue_number=42,
    data={
        "status": IssueStatus.IN_PROGRESS,
        "assigned_agent": "engineer",
        "branch_name": "feature/epic-001-42"
    }
)

# Add cycle record
cycle = state_manager.add_cycle(
    epic_id="epic-001",
    issue_number=42,
    agent_from="engineer",
    agent_to="reviewer",
    action="Submitted PR #123",
    result="PR created successfully"
)

# Check if epic is complete
is_complete = state_manager.is_epic_complete("epic-001")
if is_complete:
    state_manager.update_epic_status("epic-001", EpicStatus.COMPLETE)

# Load all state
all_state = state_manager.load()
for epic_id, epic in all_state.items():
    print(f"Epic {epic_id}: {len(epic.issues)} issues")
```

## 2. Implementing a Custom Agent

### Creating an Engineer Agent
```python
from orchestify.core import BaseAgent, AgentContext, AgentResult, Scorecard

class EngineerAgent(BaseAgent):
    """Custom engineer agent implementation."""
    
    async def execute(self, context: AgentContext) -> AgentResult:
        """Implement the task."""
        # Build LLM messages
        messages = self._build_messages(context)
        
        # Call LLM
        output, tokens = await self._call_llm(messages)
        
        # Validate output
        if not self._validate_output(output):
            return AgentResult(
                output="",
                files_changed=[],
                tokens_used=tokens
            )
        
        # Extract file changes from output
        files = self._extract_files_from_output(output)
        
        return AgentResult(
            output=output,
            files_changed=files,
            tokens_used=tokens,
            raw_response=output
        )
    
    def score(self, result: AgentResult) -> Scorecard:
        """Score the engineer's output."""
        output = result.output.lower()
        
        # Evaluate based on ABD criteria
        scope_control = 2 if len(result.files_changed) <= 5 else 1
        behavior_fidelity = 2 if "solution" in output else 1
        evidence_orientation = 2 if "```" in result.output else 1
        actionability = 2 if any(v in output for v in ["change", "add", "fix"]) else 1
        risk_awareness = 2 if "test" in output else 1
        
        return Scorecard(
            scope_control=scope_control,
            behavior_fidelity=behavior_fidelity,
            evidence_orientation=evidence_orientation,
            actionability=actionability,
            risk_awareness=risk_awareness
        )
    
    def recycle(self, result: AgentResult, scorecard: Scorecard):
        """Determine recycle strategy."""
        if scorecard.interpretation.value == "promote":
            return RecycleOutput(kept=result.files_changed)
        elif scorecard.interpretation.value == "anti-pattern":
            return RecycleOutput(banned=result.files_changed)
        else:
            return RecycleOutput(reused=result.files_changed)
```

## 3. Using the Orchestration Engine

### Full Pipeline Execution
```python
from orchestify.core import OrchestrifyEngine, StateManager
from pathlib import Path

# Setup
state_manager = StateManager(Path("/path/to/repo"))
engine = OrchestrifyEngine(
    config={"max_retries": 3, "max_self_fixes": 3},
    state_manager=state_manager,
    provider_registry={"openai": openai_provider},
    memory_client=memory_client
)

# Register all agents
engine.register_agent("tpm", tpm_agent)
engine.register_agent("architect", architect_agent)
engine.register_agent("engineer", engineer_agent)
engine.register_agent("reviewer", reviewer_agent)
engine.register_agent("qa", qa_agent)

# Run full pipeline
result = await engine.run_full_pipeline(
    prompt="Implement user authentication system"
)

if result["success"]:
    print(f"Pipeline complete for epic {result['epic_id']}")
    print(f"Issues processed: {result['issues_result']['issues_processed']}")
else:
    print(f"Pipeline failed: {result['error']}")
```

### Running Specific Phases
```python
# Run just the Architect phase
architect_result = await engine.run_phase(
    "architect",
    epic_id="epic-001"
)

# Run issue loop
loop_result = await engine.run_phase(
    "issue_loop",
    epic_id="epic-001"
)

# Get engine state
state = state_manager.load()
epic = state["epic-001"]
print(f"Issues: {len(epic.issues)}")
for issue in epic.issues:
    print(f"  Issue #{issue.issue_number}: {issue.status}")
```

## 4. Logging and Monitoring

### Structured Logging
```python
from orchestify.utils import get_logger

# Get logger for module
logger = get_logger(__name__)

# Log at different levels
logger.debug("Detailed debug info")
logger.info("Starting pipeline execution")
logger.warning("Issue escalated due to repeated failures")
logger.error("Critical error in PR merge", exc_info=True)

# Get file-specific logger
agent_logger = get_logger("agent_execution")
agent_logger.info("Engineer agent completed task")

# Logs written to:
# - .orchestify/logs/orchestify.log (file)
# - Console with Rich formatting
```

## 5. Retry Handling

### Retrying LLM Calls
```python
from orchestify.utils.retry import retry_llm_call

@retry_llm_call(max_retries=3, initial_wait=1, max_wait=32)
async def call_llm(messages):
    """Call LLM with automatic retry on failure."""
    response = await provider.call(messages)
    return response

# Usage
result = await call_llm(messages)
```

### Retrying GitHub API
```python
from orchestify.utils.retry import retry_github_call

@retry_github_call(max_retries=3, initial_wait=2, max_wait=60)
def create_pr(title, body, head, base):
    """Create PR with GitHub rate limit retry."""
    return github_client.create_pull_request(title, body, head, base)

# Usage
pr = create_pr("Fix bug", "This fixes issue #123", "feature/fix", "main")
```

## 6. Output Validation

### Validating Artifacts
```python
from orchestify.utils.validators import (
    validate_issue_format,
    validate_pr_format,
    validate_review_format,
    validate_scorecard,
    validate_evidence,
    validate_actionability
)

# Validate issue
is_valid, errors = validate_issue_format(issue_content)
if not is_valid:
    print("Issue validation errors:")
    for error in errors:
        print(f"  - {error}")

# Validate PR
is_valid, errors = validate_pr_format(pr_description)
if not is_valid:
    raise ValueError(f"Invalid PR: {errors}")

# Validate review
is_valid, errors = validate_review_format(review_content)
assert is_valid, f"Review failed validation: {errors}"

# Validate scorecard
scorecard = Scorecard(
    scope_control=2,
    behavior_fidelity=2,
    evidence_orientation=1,
    actionability=2,
    risk_awareness=1
)
is_valid, errors = validate_scorecard(scorecard)
print(f"Scorecard valid: {is_valid}, Total: {scorecard.total}")

# Validate evidence and actionability
is_evidenced, errors = validate_evidence(output, minimum_pieces=2)
is_actionable, errors = validate_actionability(output)
```

## 7. State Persistence Example

### Resuming from State
```python
# Check if previous state exists
previous_state = state_manager.load()

if previous_state:
    # Resume from last epic
    for epic_id, epic in previous_state.items():
        if epic.status == EpicStatus.IN_PROGRESS:
            print(f"Resuming epic {epic_id}")
            
            # Get next pending issue
            next_issue = state_manager.get_next_issue(epic_id)
            if next_issue:
                print(f"Resuming from issue #{next_issue.issue_number}")
                
                # Continue processing
                result = await engine._run_issue_cycle(epic_id, next_issue.issue_number)
else:
    # Start fresh
    print("No previous state, starting new pipeline")
    result = await engine.run_full_pipeline(prompt="Your task")

# State is always persisted automatically
# .orchestify/state.json contains full workflow state
```

## 8. Advanced: Custom Validation

### Extending Validators
```python
from orchestify.utils.validators import validate_evidence, validate_actionability

def validate_custom_format(content: str) -> tuple:
    """Custom validation combining multiple checks."""
    errors = []
    
    # Check evidence
    evidenced, ev_errors = validate_evidence(content, minimum_pieces=3)
    if not evidenced:
        errors.extend(ev_errors)
    
    # Check actionability
    actionable, ac_errors = validate_actionability(content)
    if not actionable:
        errors.extend(ac_errors)
    
    # Custom checks
    if content.count('\n') < 10:
        errors.append("Content must be at least 10 lines")
    
    if not any(c.isupper() for c in content):
        errors.append("Content must contain capital letters")
    
    return len(errors) == 0, errors

# Usage
is_valid, errors = validate_custom_format(agent_output)
```

## Key Patterns

### Pattern 1: Thread-Safe State Updates
```python
# All state updates are atomic and thread-safe
issue = state_manager.update_issue(
    epic_id="epic-001",
    issue_number=42,
    data={"status": IssueStatus.REVIEW, "review_cycles": 1}
)
# File lock ensures no concurrent writes
# Changes persisted immediately to .orchestify/state.json
```

### Pattern 2: Scorecard Auto-Interpretation
```python
# Scorecard automatically interprets based on total
scorecard = Scorecard(
    scope_control=2,
    behavior_fidelity=2,
    evidence_orientation=2,
    actionability=2,
    risk_awareness=0
)
# Total = 8, interpretation = "promote"
print(scorecard.interpretation)  # Interpretation.PROMOTE
```

### Pattern 3: Async Pipeline Execution
```python
# All phases and agents are async
result = await engine.run_full_pipeline(prompt="task")

# Can run phases in parallel if independent
results = await asyncio.gather(
    engine.run_phase("tpm", input_text="task"),
    engine.run_phase("architect", epic_id="epic-002")
)
```

