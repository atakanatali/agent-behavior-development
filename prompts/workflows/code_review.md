# Code Review Workflow

## Purpose
Review code changes against standards, identify issues, and ensure quality before merge.

## Input
- Pull request with code changes
- Original issue specification
- Reference to code_standards.md and domain-specific standards
- Reference to the appropriate reviewer persona (frontend, backend, iOS, Android)

## Workflow Steps

### 1. Setup & Context
- Understand the issue being addressed
- Understand what domain(s) the PR affects
- Note the engineer and their skill level (for feedback tone)
- Identify highest-risk areas to focus on

### 2. Architecture & Design Review
Check design-level questions first:

- [ ] Does this follow the established architectural pattern?
- [ ] Is code organized according to project_structure.md?
- [ ] Are separation of concerns principles followed?
- [ ] Is new functionality properly abstracted?
- [ ] Could similar code be extracted and reused?
- [ ] Are design patterns applied appropriately?
- [ ] Is complexity justified or over-engineered?

### 3. Code Quality Review

#### Standards Compliance
- [ ] SOLID principles applied
- [ ] DRY: no code duplication
- [ ] KISS: unnecessarily complex?
- [ ] YAGNI: building for hypothetical features?
- [ ] Naming: clear, consistent, follows conventions
- [ ] Code organization: logical grouping, easy to navigate

#### Language/Framework Specific
- [ ] TypeScript: proper typing, no `any` without justification
- [ ] React: hooks used correctly, no stale closures
- [ ] Swift: memory management sound, no retain cycles
- [ ] Kotlin: null safety enforced, coroutines scoped properly
- [ ] Async: async/await preferred, timeouts configured
- [ ] Database: queries optimized, indexes used

#### Testing
- [ ] Unit tests written for business logic
- [ ] Tests cover happy path and edge cases
- [ ] Integration tests validate data flows
- [ ] >80% code coverage maintained
- [ ] Tests are readable and maintain fixtures properly
- [ ] No tests of implementation details

### 4. Error Handling Review
- [ ] All error paths handled
- [ ] Errors logged with context
- [ ] User-facing error messages clear
- [ ] No silent failures
- [ ] Error types specific (not broad catch-all)

### 5. Security Review
- [ ] No hardcoded secrets
- [ ] Input validation at API boundaries
- [ ] SQL injection prevention (parameterized queries)
- [ ] XSS prevention (no dangerouslySetInnerHTML, etc.)
- [ ] CSRF protection if state-changing
- [ ] Authentication checks on protected endpoints
- [ ] Authorization checks respect user roles
- [ ] Sensitive data not exposed in logs or errors

### 6. Performance Review
- [ ] No N+1 queries
- [ ] Proper caching strategy
- [ ] Blocking operations eliminated
- [ ] Async/await used appropriately
- [ ] Bundle size impact acceptable
- [ ] No unnecessary re-renders (React)
- [ ] No memory leaks (lifecycle cleanup)

### 7. Domain-Specific Review

**Frontend Focus:**
- Component API clear and documented
- Responsive design tested on mobile
- Accessibility: semantic HTML, ARIA, keyboard nav, color contrast
- Dark mode support
- Performance: bundle size, Core Web Vitals

**Backend Focus:**
- API design follows REST principles
- Database schema changes have migration
- Error response format consistent
- Logging comprehensive and structured
- Rate limiting considered if public API

**iOS Focus:**
- MVVM pattern applied
- Memory management sound
- Lifecycle properly managed
- Accessibility and VoiceOver support
- HIG compliance

**Android Focus:**
- MVVM pattern applied
- Coroutines scoped properly
- Lifecycle properly managed
- Accessibility and TalkBack support
- Material Design 3 compliance

### 8. Logging & Observability
- [ ] Structured logging used
- [ ] Context included (request ID, user ID, correlation ID)
- [ ] Log levels appropriate (DEBUG, INFO, WARN, ERROR)
- [ ] Sensitive data not logged
- [ ] Enough logged for debugging

### 9. Documentation
- [ ] Code comments explain "why", not "what"
- [ ] Complex logic documented
- [ ] Public API documented (JSDoc, KDoc, etc.)
- [ ] README updated if needed
- [ ] Architecture decisions explained in comments

### 10. Prepare Review Feedback

#### Categorize Findings
- **Blocking Issues**: Must fix before merge
  - Security vulnerabilities
  - Architectural violations
  - Breaking changes
  - Test failures
  - Type errors

- **Major Issues**: Should fix (can discuss exceptions)
  - Performance problems
  - Error handling gaps
  - Missing tests
  - Code quality significantly below standard

- **Suggestions**: Nice to have
  - Style improvements
  - Minor refactoring opportunities
  - Documentation improvements
  - Optimization ideas

#### Write Review Comments
For each finding:
1. Reference specific code line(s)
2. Explain the issue clearly
3. Suggest a fix if not obvious
4. Explain why it matters
5. Be respectful and constructive

Example good feedback:
```
Line 45-48: This N+1 query pattern will cause performance issues at scale.
Instead of fetching users in a loop within the service, fetch all IDs first,
then fetch users in a single batch query:

const userIds = orders.map(o => o.userId);
const users = await db.users.whereIn('id', userIds);
```

Example bad feedback:
```
This is inefficient.
```

### 11. Make Decision

#### Approve
- All blocking issues resolved
- No major issues, or major issues have accepted tradeoffs
- Code meets quality standards
- Tests adequate
- Ready to merge

#### Request Changes
- Blocking issues must be addressed
- Major issues should be addressed
- Provide clear guidance on what needs to change

#### Comment
- Informational feedback
- Not blocking
- Author should consider addressing
- Discussion may be helpful

### 12. Summary Comment

If review has blocking issues or major findings, provide summary:

```
## Code Review Summary

### Overview
This PR implements user authentication flow with login/logout and token management.

### Strengths
- Good error handling and user feedback
- Test coverage is comprehensive
- Clean separation between auth service and UI

### Issues to Address

**Blocking:**
1. Line 45: N+1 query when fetching user roles (see comment)
2. Line 78: Missing null check on response data

**Major:**
1. Password reset endpoint doesn't validate email format (line 156)
2. Missing integration tests for token refresh flow

**Suggestions:**
1. Consider extracting auth header logic into utility function
2. Add request correlation ID to auth logs for debugging

### Approval Conditions
Once blocking issues are fixed and major issues addressed, this is ready to merge.
```

## Output Format

Review output includes:

```
## Code Review: [PR Title/Issue]

### Status: [APPROVE|REQUEST CHANGES|COMMENT]

### Findings

#### Blocking Issues (Must Fix)
- Issue 1: [description with line reference]
  Fix: [suggested solution]

- Issue 2: [description with line reference]
  Fix: [suggested solution]

#### Major Issues (Should Fix)
- Issue 1: [description with line reference]
  Suggestion: [recommended approach]

#### Suggestions (Nice to Have)
- Suggestion 1: [improvement idea]
- Suggestion 2: [improvement idea]

### Strengths
- Strength 1
- Strength 2

### Comments
[Any general observations or praise]

### Approval Status
[Ready to merge | Needs fixes | Hold for discussion]
```

## Quality Checklist for Reviewers

- [ ] Understood the issue being addressed
- [ ] Reviewed for architectural compliance
- [ ] Checked SOLID principle compliance
- [ ] Verified tests exist and cover cases
- [ ] Reviewed error handling
- [ ] Checked security implications
- [ ] Verified performance is acceptable
- [ ] Checked domain-specific standards
- [ ] Reviewed logging and observability
- [ ] Verified code clarity and maintainability
- [ ] Made clear decision (Approve/Request/Comment)
- [ ] Provided constructive, specific feedback
- [ ] Explained "why" not just "fix this"

## Escalation Points

Stop and request architect involvement when:
- Code violates core architectural principles
- Pattern violation affects system scalability
- Security issue is systemic, not just in this PR
- Performance degradation would affect 100M+ users
- Breaking change not previously discussed
