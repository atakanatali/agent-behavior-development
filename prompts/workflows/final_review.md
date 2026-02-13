# Final Review Workflow

## Purpose
Architect final validation before merge to ensure architectural compliance, project structure integrity, and system-wide consistency.

## Input
- Pull request with all code changes and reviews completed
- Reference to prompts/guidelines/architecture.md
- Reference to prompts/guidelines/project_structure.md
- All code review feedback (from domain reviewers)
- QA test results and sign-off
- Original issue specification

## Workflow Steps

### 1. Preparation
- Understand the feature being delivered
- Review all prior feedback from code reviewers
- Review QA findings and sign-off status
- Assess urgency (blocker, normal, enhancement)
- Identify if this touches multiple domains/services

### 2. Architecture Compliance Review

#### Architectural Pattern Compliance
- [ ] Design follows reference architecture (prompts/guidelines/architecture.md)
- [ ] Modular Monolith pattern respected (if applicable)
- [ ] gRPC used for internal communication (not REST)
- [ ] REST used for public APIs (not gRPC)
- [ ] CQRS applied where appropriate
- [ ] Event-driven patterns used correctly
- [ ] No architectural shortcuts or hacks
- [ ] Design supports 100M+ scale requirements

#### SOLID Principles
- [ ] Single Responsibility: each component has one reason to change
- [ ] Open/Closed: extensible without modification
- [ ] Liskov Substitution: abstractions properly implemented
- [ ] Interface Segregation: dependencies focused
- [ ] Dependency Inversion: depends on abstractions
- [ ] No violations of core principles

#### System Integration
- [ ] Changes don't break existing services
- [ ] API contracts maintained or versioned
- [ ] No direct coupling between services
- [ ] Event contracts consistent with event schema
- [ ] Data model changes consider downstream consumers
- [ ] Backward compatibility maintained or planned

### 3. Project Structure Validation

#### Directory Organization
- [ ] Code organized per prompts/guidelines/project_structure.md
- [ ] New files in appropriate locations
- [ ] No files in wrong domains or layers
- [ ] Shared code properly isolated in /shared
- [ ] No cross-domain imports outside approved patterns

#### Layering (Backend)
If backend code:
- [ ] Presentation layer only handles HTTP/gRPC
- [ ] Application layer orchestrates business logic
- [ ] Domain layer contains business rules (no framework code)
- [ ] Infrastructure layer handles data access and external APIs
- [ ] Shared layer contains common types and utilities
- [ ] No business logic in presentation or infrastructure layers

#### Component Organization (Frontend)
If frontend code:
- [ ] Components logically organized by feature
- [ ] Shared components in /components/shared
- [ ] Hooks in /hooks with clear responsibility
- [ ] Services/utils properly abstracted
- [ ] No business logic in component render

#### Platform Organization (Mobile)
If iOS/Android code:
- [ ] iOS code in /ios directory
- [ ] Android code in /android directory
- [ ] ViewModels in appropriate layer
- [ ] Models properly shared via /shared/models
- [ ] Services abstracted correctly

### 4. Code Quality Review (Architect Perspective)

Check domain reviewers' feedback:
- [ ] All code reviewers approved (or concerns resolved)
- [ ] No unresolved blocking feedback
- [ ] Performance concerns addressed
- [ ] Security concerns addressed
- [ ] Testing adequate

### 5. Database Changes Review (if applicable)

- [ ] Schema migrations provided
- [ ] Migrations are backwards compatible
- [ ] Rollback strategy documented
- [ ] Indexes added for query performance
- [ ] No breaking schema changes without versioning
- [ ] Data migration path clear (if needed)
- [ ] Foreign key constraints appropriate
- [ ] Denormalization justified for performance
- [ ] Sharding/partitioning strategy if needed

### 6. API Design Review

Check API contracts:
- [ ] REST principles followed (if REST API)
- [ ] Resource-based endpoints, not RPC-style
- [ ] HTTP methods used semantically
- [ ] Status codes correct and consistent
- [ ] Error response format standard
- [ ] Pagination implemented (for list endpoints)
- [ ] Versioning strategy clear
- [ ] OpenAPI documentation accurate
- [ ] Rate limiting considered (if public)
- [ ] CORS policies appropriate

### 7. Security & Compliance

- [ ] All security reviews completed
- [ ] No hardcoded secrets or credentials
- [ ] Authentication/authorization checks in place
- [ ] Input validation at boundaries
- [ ] OWASP risks mitigated
- [ ] Data encryption at rest and in transit
- [ ] Secrets management strategy appropriate
- [ ] Compliance requirements met (GDPR, etc.)

### 8. Performance & Scale

- [ ] Design supports 100M+ users
- [ ] Database queries optimized (no N+1)
- [ ] Caching strategy appropriate
- [ ] Async operations don't block
- [ ] Monitoring/observability points included
- [ ] Performance baselines met
- [ ] Scalability bottlenecks identified and mitigated

### 9. Testing Validation

- [ ] Code review testing requirements met
- [ ] QA approved feature
- [ ] Performance tests run
- [ ] Security tests run
- [ ] Regression testing completed
- [ ] Acceptance criteria verified
- [ ] Edge cases covered
- [ ] Error scenarios handled

### 10. Documentation Check

- [ ] Code comments explain "why" not "what"
- [ ] Complex algorithms documented
- [ ] Architecture decisions explained
- [ ] API documented (OpenAPI/AsyncAPI)
- [ ] Database schema documented
- [ ] Setup/deployment instructions clear
- [ ] Breaking changes documented
- [ ] Migration guide provided (if needed)

### 11. Release Readiness Assessment

Checklist:
- [ ] All code reviews approved
- [ ] QA approved (or issues resolved)
- [ ] Architecture compliant
- [ ] Performance acceptable
- [ ] Security verified
- [ ] Project structure intact
- [ ] Tests passing
- [ ] Documentation complete
- [ ] Deployment strategy clear
- [ ] Rollback plan ready

### 12. Make Approval Decision

#### Approve for Merge
Conditions all met:
- All architectural requirements satisfied
- Code quality standards met
- Security and performance verified
- Testing completed and passing
- Documentation adequate

Approval comment:
```
## Architectural Sign-off

This PR is approved for merge.

### Verification
- Architecture: Compliant with Modular Monolith pattern
- SOLID: All principles respected
- Structure: Correct organization per project structure
- Security: Input validation and auth checks verified
- Performance: Queries optimized; design supports 100M+ scale
- Tests: Code coverage adequate; QA approved
- Documentation: API documented; architecture clear

### Notes
- Consider monitoring [specific metric] in production
- Database migration well-designed; safe to deploy
- No architectural debt introduced

Ready to merge and deploy.
```

#### Request Changes
If issues found:
```
## Architectural Review - Issues Found

This PR requires changes before merge.

### Blocking Issues
1. **Architecture**: Service A directly importing from Service B (line 45)
   - Fix: Use event-driven communication instead
   - Reference: prompts/guidelines/architecture.md section on cross-service communication

2. **Security**: API endpoint missing authorization check (line 78)
   - Fix: Add @RequireAuth decorator
   - Verify: QA will test this after fix

### Major Issues
1. **Structure**: New file in wrong location (should be in /domain, not /models)
   - Move file to appropriate location

2. **Performance**: N+1 query pattern in UserService
   - Fetch user IDs first, then fetch all users in single batch

### Approval Conditions
- [ ] Address blocking architecture issue
- [ ] Move file to correct location
- [ ] Fix N+1 query pattern
- [ ] Verify QA re-tests authorization
- [ ] Resubmit for final review

This is a good approach overall; these changes will ensure long-term maintainability.
```

#### Hold for Discussion
If uncertainty exists:
```
## Architectural Review - Hold for Discussion

This PR introduces a new pattern that needs team discussion before approval.

### Discussion Point
The use of GraphQL for the user service is a departure from our REST standard.
While GraphQL has benefits, we should discuss:
- Impact on mobile clients
- Caching strategy
- Team expertise and maintenance burden

### Next Steps
Schedule sync with core architecture team to discuss GraphQL adoption.
This PR can proceed once team consensus is reached.

Timeline: [propose resolution timeline]
```

### 13. Track for Monitoring

If approved, note:
- Special monitoring requirements
- Performance baselines to establish
- Security aspects to monitor
- Potential rollback triggers

Example:
```
## Post-Deployment Monitoring

Monitor these metrics for the first week:
- API endpoint latency (should stay <200ms)
- Database query times (no regressions)
- Error rate (should stay <0.1%)
- Server memory usage (should remain stable)

Rollback triggers:
- Error rate exceeds 1%
- Any database corruption detected
- Critical security vulnerability found
```

## Output Format

Final review output:

```
# Architectural Final Review

## Feature: [Name]
## PR: [Link]
## Reviewer: @architect
## Date: [Date]

## Review Status: [APPROVED|REQUEST CHANGES|HOLD FOR DISCUSSION]

### Architectural Compliance
- [ ] Follows reference architecture
- [ ] SOLID principles respected
- [ ] Project structure correct
- [ ] API design compliant
- [ ] Database design sound

### Quality Verification
- [ ] Code reviews completed: [Yes, all approved]
- [ ] QA sign-off: [Yes, approved]
- [ ] Security review: [Yes, cleared]
- [ ] Performance verified: [Yes, acceptable]
- [ ] Tests: [Passing, >80% coverage]

### Issues Found (if any)
[List blocking and major issues with fixes]

### Approval Notes
[Special considerations, monitoring needs, etc.]

### Decision
[APPROVED FOR MERGE | NEEDS FIXES | HOLD FOR DISCUSSION]
```

## Quality Checklist

- [ ] Architecture reviewed against standards
- [ ] SOLID principles verified
- [ ] Project structure validated
- [ ] Database design sound (if applicable)
- [ ] API design verified (if applicable)
- [ ] Security concerns addressed
- [ ] Performance implications understood
- [ ] Testing adequate
- [ ] Code quality standards met
- [ ] Documentation complete
- [ ] All prior reviews resolved
- [ ] Clear approval decision made

## Escalation Points

Stop and escalate when:
- Architectural pattern doesn't match standards
- Project structure severely violated
- Database design raises scale concerns
- API design conflicts with existing contracts
- Security concerns require senior review
- Performance would limit scaling
- Team consensus needed on new patterns
