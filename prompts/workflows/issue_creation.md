# Issue Creation Workflow

## Purpose
Convert a comprehensive specification into discrete, implementable issues that can be distributed to engineering teams.

## Input
- Completed specification document
- Reference to prompts/guidelines/project_structure.md
- Reference to prompts/guidelines/architecture.md
- Any existing related issues or epics

## Workflow Steps

### 1. Analyze Specification for Discrete Work Units
- Read specification completely
- Identify distinct features or components
- Identify dependencies between pieces
- Estimate complexity of each piece
- Group by domain: frontend, backend, iOS, Android, shared

### 2. Break Into Issues
- Each issue should represent approximately 15-20 changes
- Each issue should be independently implementable
- Each issue should be independently reviewable
- Each issue should be independently testable
- Avoid issues that require multiple unreleased PRs to complete

Splitting strategy:
- By domain (frontend issue, backend issue, iOS issue, etc.)
- By layer (API design, database schema, business logic, UI)
- By feature area (if large feature)
- By execution phase (MVP first, then enhancements)

### 3. Define Issue Sequence
- Identify blocking dependencies: issue A must complete before B starts
- Identify parallel work: issues that can be done concurrently
- Suggest execution order with rationale
- Flag if splitting should change based on dependencies

### 4. Create Epic Structure
- Group related issues into epics
- Epic should represent a cohesive feature or major piece
- Order issues within epic by execution sequence
- Document epic goal and success criteria

### 5. For Each Issue, Create Details

#### Issue Title
- Clear, specific, no jargon
- Include domain if not obvious: [Backend] User authentication
- Action-oriented: "Implement", "Add", "Refactor", not "Fix"

#### Agent Directive
- Specify which engineer role should handle: @engineer_frontend, @engineer_backend, etc.
- Include reviewer directive: @reviewer_frontend
- For architecture work: @architect

#### Goal
- One sentence: what is this issue trying to accomplish
- Business or user outcome focused

#### Context
- Why does this issue exist?
- How does it fit into the larger feature?
- What does it depend on?
- What depends on it?

#### Acceptance Criteria
- Specific, testable requirements
- Clear definition of "done"
- Include error cases if applicable
- Reference specific fields, endpoints, or components

#### Behavior Specification
- Detailed description of what needs to be built
- Edge cases and error scenarios
- Performance requirements if applicable
- Security considerations if applicable
- Include examples or data structures if relevant
- Reference architecture patterns (SOLID, DRY, etc.)

#### Technical Details
- Affected files or layers
- Database schema changes (if applicable)
- API changes (if applicable)
- State management implications
- Performance implications
- Security implications

#### Done Checklist
- Code written and tested
- Tests pass (unit and integration)
- Code reviewed and approved
- PR merged
- Acceptance criteria verified
- Documentation updated (if needed)
- Performance verified (if applicable)

#### Risks & Considerations
- What could go wrong?
- What's the hardest part?
- What needs investigation?
- What could cause rework?
- Performance bottlenecks?
- Security concerns?

## Output Format

Each issue should follow this structure:

```
# Issue: [Agent Directive] [Title]

## Goal
[One sentence goal]

## Context
[Why this issue exists, how it fits into larger feature]

## Acceptance Criteria
- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Criterion 3

## Behavior Specification
[Detailed description of what needs to be built]

### Example
[Example or data structure]

### Edge Cases
[Edge cases and how they should be handled]

### Error Scenarios
[Error scenarios and expected handling]

## Technical Approach
- Affected files/layers: [list]
- Architecture patterns: [patterns to follow]
- Dependencies: [what this depends on]
- Performance: [performance requirements]

## Done Checklist
- [ ] Implementation complete
- [ ] Unit tests written and passing
- [ ] Integration tests written and passing
- [ ] Code review approved
- [ ] Acceptance criteria verified
- [ ] Performance verified (if applicable)
- [ ] Documentation updated (if needed)

## Risks & Considerations
- Risk 1: [mitigation strategy]
- Risk 2: [mitigation strategy]
- Consideration 1: [note for implementer]

## Related Issues
[Link to related or dependent issues]
```

### Epic Template
```
# Epic: [Feature Name]

## Goal
[What this epic accomplishes]

## Acceptance Criteria
- [ ] All related issues complete
- [ ] Feature works end-to-end
- [ ] Performance verified
- [ ] QA sign-off

## Issues
1. [Issue 1] - [Blocking issues or "no dependencies"]
2. [Issue 2] - [Depends on Issue 1]
3. [Issue 3] - [Can be parallel with Issue 2]

## Execution Notes
[Any special considerations for executing this epic]

## Success Metrics
[How will we know this feature is successful?]
```

## Quality Checklist

For each issue:
- [ ] Title is clear and action-oriented
- [ ] Agent directive is specific (which engineer role)
- [ ] Acceptance criteria are testable and objective
- [ ] Behavior specification is detailed enough to implement
- [ ] Technical approach is clear
- [ ] Risks are identified
- [ ] Issue is approximately 15-20 changes (not huge, not tiny)
- [ ] Issue can be reviewed and tested independently
- [ ] Done checklist is complete and realistic

For the entire issue set:
- [ ] All issues together implement the specification
- [ ] Issues are sequenced correctly
- [ ] Dependencies are identified
- [ ] Issues are grouped into logical epics
- [ ] No issue is blocked by more than 2-3 others
- [ ] Distribution across teams is balanced

## Escalation Points

Stop and escalate when:
- Specification has ambiguities that prevent issue creation
- Issue is so large it needs further breaking down
- Issue requires architectural decision not yet made
- Dependency chain is too long or complex
- Issue can't be tested independently
- Issue doesn't match any single domain (requires simultaneous work)
