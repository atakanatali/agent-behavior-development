# Technical Design Workflow

## Purpose
Review issues for technical feasibility, enrich with architecture details, assign domain labels, and ensure compliance with architectural standards.

## Input
- List of issues from issue creation workflow
- prompts/guidelines/architecture.md (reference architecture)
- prompts/guidelines/project_structure.md (project structure reference)
- Current codebase state and constraints

## Workflow Steps

### 1. Review Issue List for Completeness
- Confirm all issues follow ABD template
- Verify all issues have agent directives
- Check that acceptance criteria are clear
- Identify any gaps in issue specification

### 2. Architectural Feasibility Review
For each issue:

#### Check Against Architecture Guidelines
- Does issue respect Modular Monolith pattern (if applicable)?
- Are API design principles followed (REST for public, gRPC for internal)?
- Does issue leverage CQRS where appropriate?
- Are event-driven patterns used for cross-service communication?
- Is design suitable for 100M+ scale?

#### Check SOLID Compliance
- Single Responsibility: does this component/service do one thing?
- Open/Closed: extensible without modification?
- Liskov Substitution: proper abstraction hierarchy?
- Interface Segregation: not forcing unnecessary dependencies?
- Dependency Inversion: depends on abstractions, not concretions?

#### Check Code Standards Compliance
- DRY: no duplicated logic across issues?
- KISS: is solution as simple as needed?
- YAGNI: not building for hypothetical future features?

### 3. Domain Assignment
For each issue, assign one or more labels:
- **frontend**: React/Next.js components, client-side state, UI logic
- **backend**: API endpoints, business logic, database operations
- **ios**: Swift/SwiftUI code, iOS-specific features
- **android**: Kotlin/Compose code, Android-specific features
- **shared**: Shared utilities, DTOs, contracts used by multiple domains

Rules:
- Frontend + Backend: if feature requires both (typical for new feature)
- Mobile (iOS + Android): if feature needs to be implemented on both platforms
- One primary domain: if issue clearly belongs in one place

### 4. Identify Technical Constraints & Decisions
For each issue, document:

#### Database Changes (if applicable)
- Schema migrations required?
- Indexes needed?
- Partitioning strategy for scale?
- Data migration or backfill?
- Backward compatibility?

#### API Contracts (if applicable)
- REST endpoints: method, path, request body, response body
- Error responses: standard error format
- Pagination: strategy and parameters
- Versioning: v1, v2, content negotiation?
- OpenAPI documentation requirements

#### Architecture Patterns
- State management approach
- Event handling approach
- Error handling patterns
- Caching strategy
- Async/await patterns
- Data validation approach

#### Performance & Scale Considerations
- Expected data volumes
- Query complexity analysis
- Caching requirements
- Connection pooling strategy
- Monitoring and observability requirements

#### Security Considerations
- Authentication requirements
- Authorization checks needed
- Input validation strategy
- Data encryption (at rest, in transit)
- Secrets management
- Third-party integration security

### 5. Split Oversized Issues
If issue is too large (>30 changes estimated):
- Identify natural split points
- Create sub-issues
- Document dependencies
- Explain why it couldn't be smaller

### 6. Create Architecture Review Notes
For each issue, add:

#### Architecture Analysis
- Pattern compliance: which patterns does this follow?
- Tradeoffs made: why this approach over alternatives?
- Future implications: how does this affect scaling?

#### Code Organization
- Where does this code live in project structure?
- Any new directories or modules needed?
- Alignment with existing patterns

#### Testing Strategy
- Unit test approach
- Integration test approach
- Performance test approach (if applicable)
- Security test approach (if applicable)

#### Dependency Analysis
- Internal dependencies (which issues depend on this?)
- External dependencies (libraries, services)
- Version constraints or conflicts?

### 7. Create Technical Design Document
Combine all issues with architectural enrichment:

```
# Technical Design: [Feature Name]

## Architecture Overview
[How this feature fits into system architecture]

## Design Patterns
- Pattern 1: [where and why]
- Pattern 2: [where and why]

## Data Model
[Schema changes, new entities, relationships]

## API Contracts
- Endpoint 1: [method, path, request, response]
- Endpoint 2: [method, path, request, response]

## Issues by Domain

### Frontend Issues
- Issue 1: [title] - Dependencies: [list]
- Issue 2: [title] - Dependencies: [list]

### Backend Issues
- Issue 1: [title] - Dependencies: [list]
- Issue 2: [title] - Dependencies: [list]

### iOS Issues
[List of iOS issues with dependencies]

### Android Issues
[List of Android issues with dependencies]

### Shared Issues
[List of shared issues with dependencies]

## Execution Strategy
- Phase 1: [issues, rationale]
- Phase 2: [issues, rationale]
- Phase 3: [issues, rationale]

## Performance & Scale Analysis
[How this design handles 100M+ users]

## Security Analysis
[Security considerations and mitigations]

## Risks & Mitigations
- Risk 1: [mitigation]
- Risk 2: [mitigation]
```

## Quality Checklist

- [ ] All issues reviewed for architectural compliance
- [ ] SOLID principles verified in design
- [ ] Domain labels assigned correctly
- [ ] Oversized issues identified and split
- [ ] Architecture decisions documented with reasoning
- [ ] Database changes have migration strategy
- [ ] API contracts are well-defined
- [ ] Performance implications considered
- [ ] Security implications addressed
- [ ] Testing strategy defined for each issue
- [ ] Execution sequence optimized
- [ ] Technical design document complete

## Escalation Points

Stop and escalate when:
- Issue violates core architectural principles
- Feature requires new architectural pattern not yet approved
- Database scaling strategy isn't clear
- Performance requirements can't be met with current design
- Security threat model reveals concerns
- Team consensus on architecture decision can't be reached
- Issue dependencies form a cycle
