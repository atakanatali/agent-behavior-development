# Spec Gathering Workflow

## Purpose
Convert high-level user requests into comprehensive, structured specifications that serve as input for issue creation.

## Input
- User request or feature description
- Any provided context (business requirements, user stories, mockups)
- Existing system documentation (architecture, project structure)

## Workflow Steps

### 1. Analyze User Input
- Read the user request completely and carefully
- Identify the core problem being solved
- Extract explicit requirements
- Note any assumptions being made
- Identify the target domain(s): frontend, backend, iOS, Android, or combination

### 2. Identify Ambiguities
- What is unclear in the request?
- What technical details are missing?
- What edge cases aren't covered?
- What error scenarios aren't specified?
- What performance or scale implications exist?
- What security concerns are relevant?

### 3. Generate Clarifying Questions
- Prioritize by criticality and impact
- Ask 2-5 questions (adjust based on complexity and ambiguity level)
- Each question should be specific and actionable
- Group related questions together
- Provide context for why each question matters

### 4. Document Current Understanding
- Summarize what you understand about the request
- List all assumptions being made
- State what needs clarification
- Ask: "Is this understanding correct?"

### 5. Produce Comprehensive Specification
Once ambiguities are addressed:

#### Problem Statement
- What problem does this solve?
- Why is it important?
- Who does it serve?
- What's the business impact?

#### User Stories & Flows
- Primary user flows (happy path)
- Secondary flows (edge cases, alternatives)
- User roles involved
- Preconditions and postconditions

#### Acceptance Criteria
- Specific, testable criteria
- Clear success metrics
- Performance baselines if applicable
- Scale requirements (users, data volume, requests/sec)

#### Technical Context
- Affected systems and domains
- Integration points
- Data models involved
- API contracts if applicable
- Database schema changes if needed

#### Error Handling Strategy
- What errors can occur?
- How should each be handled?
- What should users see?
- What should be logged?

#### Non-Functional Requirements
- Performance: response times, throughput
- Scale: current and future user counts
- Availability: uptime requirements
- Security: data sensitivity, compliance
- Accessibility: WCAG compliance required?

#### Dependencies & Constraints
- External systems or services
- Data migration requirements
- Breaking changes?
- Backward compatibility needs?
- Timeline or resource constraints?

#### Open Questions or Risks
- What's still unclear?
- What could go wrong?
- What needs further research?
- What's highest risk?

## Output Format

```
# Specification: [Feature Name]

## Problem Statement
[Why this feature exists, business impact]

## User Stories
### Story 1: [Role] - [Goal]
[Acceptance criteria]

### Story 2: [Role] - [Goal]
[Acceptance criteria]

## User Flows
[Primary flows with steps]

## Acceptance Criteria
- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Criterion 3

## Technical Context
- Affected domains: [frontend/backend/ios/android/etc]
- Integration points: [systems this touches]
- Data model: [entities and relationships]
- API contracts: [endpoints if applicable]

## Error Handling
- Error scenario 1: [How to handle]
- Error scenario 2: [How to handle]

## Non-Functional Requirements
- Performance: [targets]
- Scale: [user counts, data volumes]
- Security: [requirements]
- Accessibility: [WCAG level]

## Dependencies & Constraints
- Dependencies: [list]
- Constraints: [list]

## Risks & Unknowns
- Risk 1: [mitigation]
- Risk 2: [mitigation]
- Unknown: [what needs research]
```

## Quality Checklist

- Specification is detailed enough that engineer unfamiliar with system could implement
- All ambiguities have been addressed or explicitly called out
- Acceptance criteria are testable and objective
- Error handling strategy is explicit
- Technical context is sufficient for issue creation
- Risks are identified
- Scale and performance requirements are clear
- Security implications are considered
- All assumptions are documented

## Escalation Points

Stop and escalate when:
- Critical information can't be obtained after 3 clarifying questions
- Requirements conflict with architectural constraints
- Scope is so large it should be broken into multiple features
- Performance or scale requirements exceed current system capacity
- Stakeholder alignment is missing on problem definition
