# Issue Creation Guidelines

Standards that all issues must meet to be implementation-ready.

## Issue Quality Standards

### Completeness Checklist
Every issue must have ALL of these sections:
- [ ] Issue title (clear, action-oriented)
- [ ] Agent directive (@engineer_frontend, @engineer_backend, etc.)
- [ ] Goal (one sentence)
- [ ] Context (why, dependencies, what enables)
- [ ] Acceptance criteria (specific, testable)
- [ ] Behavior specification (detailed description)
- [ ] Technical approach (architecture, patterns, constraints)
- [ ] Done checklist (completion criteria)
- [ ] Risks & considerations (what could go wrong)

**Issues missing any section will be sent back.**

## Language & Clarity

### All Issues in English
- Clear, professional English
- Technical precision (no jargon without explanation)
- Consistent terminology
- No abbreviations unless universally understood

### Clarity Requirement
- **Single engineer unfamiliar with system** should be able to implement from issue
- Ambiguity is the enemy (will cause rework)
- Explain edge cases, not just happy path
- Provide examples and data structures

### Specificity Required
```
Bad: "Fix login"
Good: "[Backend] Implement user login endpoint with session management"

Bad: "Make it faster"
Good: "[Backend] Optimize user query from 500ms to <100ms by adding database index on email field"

Bad: "Add validation"
Good: "[Frontend] Add password validation: minimum 8 characters, at least one number, real-time feedback"
```

## Acceptance Criteria Requirements

### Criteria Must Be Testable
```
Bad: "Login should work"
Good: "User can login with valid email and password, system creates session token, user is redirected to dashboard"

Bad: "Code should be clean"
Good: "All functions <50 lines, cyclomatic complexity <10, code review approved by @reviewer_backend"

Bad: "Perform well"
Good: "API response <500ms at p95, database query <100ms, load tested with 100 concurrent requests"
```

### Acceptance Criteria Format
- Start with "User can..." or "System should..." or "Feature must..."
- Specific and measurable
- Include edge cases if relevant
- Include error scenarios if relevant

### Example Complete Criteria
```
User Login Acceptance Criteria:
- [ ] User can login with valid email/password
- [ ] System creates secure session token stored in httpOnly cookie
- [ ] User is redirected to /dashboard on successful login
- [ ] Failed login shows error "Email or password incorrect"
- [ ] Account is locked after 5 failed attempts in 15 minutes
- [ ] Locked account shows error "Account locked, try again in 15 minutes"
- [ ] Password is hashed with bcrypt (not stored plaintext)
- [ ] API endpoint responds <500ms at p95
- [ ] 100 concurrent login requests handled without corruption
- [ ] Invalid email format shows inline validation error
- [ ] SQL injection attempts prevented (parameterized queries)
- [ ] XSS attempts in email field prevented (HTML escaped)
```

## Behavior Specification Requirements

### Must Include

#### Primary User Flow
Step-by-step description of main happy path:
```
1. User opens login page
2. User enters email: user@example.com
3. User enters password
4. User clicks "Sign In" button
5. System validates inputs (not empty, valid email format)
6. System queries database for user by email
7. System verifies password hash matches
8. System generates JWT token
9. System sets secure httpOnly cookie with token
10. System redirects to /dashboard
11. User sees personalized dashboard
```

#### Error Scenarios
Each error path:
```
Error: Invalid email format
- Trigger: User enters "notanemail"
- Response: Show inline error "Enter valid email"
- Behavior: Form stays open, user can correct

Error: Account not found
- Trigger: User enters email that doesn't exist
- Response: Generic error "Email or password incorrect"
- Behavior: Prevent account enumeration

Error: Too many attempts
- Trigger: 5 failed logins in 15 minutes
- Response: Account locked, show "Try again in 15 minutes"
- Behavior: Temporary lockout with exponential backoff
```

#### Edge Cases
Boundary conditions and unusual scenarios:
```
Edge Case: Very long password (200+ characters)
- Expected: Accept and hash normally

Edge Case: Email with special characters
- Examples: user+tag@example.com, first.last@example.co.uk
- Expected: Accept all RFC 5321 compliant emails

Edge Case: Rapid repeated requests
- Scenario: User clicks submit button 5 times rapidly
- Expected: Only one login attempt processed

Edge Case: Session expires during use
- Scenario: Token expires while user on dashboard
- Expected: Auto-logout and redirect to login
```

#### Data Models
Show request/response formats with examples:
```json
Login Request:
{
  "email": "user@example.com",
  "password": "securepassword123"
}

Login Response (Success):
{
  "success": true,
  "user": { "id": "user_123", "email": "user@example.com", "name": "John" },
  "session": { "expiresIn": 86400 }
}

Login Response (Error):
{
  "success": false,
  "error": "INVALID_CREDENTIALS",
  "message": "Email or password incorrect"
}
```

#### Performance Requirements
- Response time targets: "<500ms at p95"
- Database query targets: "<100ms"
- Load requirements: "100 concurrent requests"
- Caching strategy: "Cache user preferences, invalidate on update"

#### Security Requirements
- Authentication: "Require valid session token"
- Authorization: "User can only access own data"
- Encryption: "HTTPS required, passwords hashed with bcrypt"
- Validation: "Email format validated, SQL injection prevented"

## Technical Approach Requirements

### Must Specify

#### Architecture Pattern
- Which pattern applies? (MVVM, MVC, Repository, etc.)
- Why this pattern? (justification)
- How it affects design? (layers, separation of concerns)

#### Layer/Component Identification
- What system/service? (which backend service, frontend app, etc.)
- What module/package? (where in project structure)
- Which existing code interacts? (what components/services need updates)

#### Database Changes (if applicable)
- Schema changes: "Add users table with fields: id, email, password_hash, created_at"
- Indexes: "Add index on email for login query optimization"
- Migrations: "Migration script to add users table"

#### API Changes (if applicable)
- Endpoints: "POST /api/auth/login"
- Request schema: Show example above
- Response schema: Show example above
- Status codes: "200 success, 400 validation error, 401 unauthorized, 429 rate limited"

#### State Management (frontend)
- Where state lives: "Zustand store for auth state"
- What state? "{ isAuthenticated, user, loading, error }"
- Updates? "fetchUser() updates on login, clearUser() on logout"

#### Integration Points
- What systems does this touch?
- What APIs does this call?
- What data does this depend on?

## Done Checklist Requirements

### Checklist Must Be Specific
```
Bad:
- [ ] Code written
- [ ] Tests pass
- [ ] Approved

Good:
- [ ] Implementation complete per specification
- [ ] All acceptance criteria met
- [ ] Unit tests written: happy path, error scenarios, edge cases
- [ ] Unit tests passing
- [ ] Integration tests written: full login flow
- [ ] Integration tests passing
- [ ] Code review completed by @reviewer_backend
- [ ] Code review approved (all feedback addressed)
- [ ] QA testing completed
- [ ] QA approved (all acceptance criteria verified)
- [ ] Performance verified (<500ms response time)
- [ ] Security verified (no SQL injection, XSS, rate limiting working)
- [ ] Documentation updated (API docs, inline comments)
```

### Checklist Items Must Be Actionable
- Each item should be verifiable by a specific person
- Each item should be completable in one step
- Each item should be independent (not dependent on other checklist items)

## Risks & Considerations Requirements

### Risks Must Be Specific
```
Bad:
- Risk: Performance might be slow
  Mitigation: Optimize later

Good:
- Risk: N+1 query problem when fetching user+customer data
  Impact: Could cause 50x slowdown with large datasets
  Mitigation: Use batch query to fetch all customers in one call
  Verification: Load test with 1000 users
```

### Risk Severity
- **Critical**: Could block feature or cause production issue
- **Major**: Significant impact if it happens
- **Minor**: Low probability or low impact

### Mitigation Strategy
- How to prevent the risk? (design decision)
- How to detect if it occurs? (monitoring/testing)
- What to do if it happens? (fallback plan)

## Agent Directive Requirements

### Must Be Specific
```
Bad: @engineer (which engineer?)

Good:
- @engineer_backend (backend engineer implements API)
- @engineer_frontend (frontend engineer implements UI)
- @engineer_ios (iOS engineer implements mobile)
- @engineer_android (Android engineer implements mobile)
- @architect (architect makes design decisions)
- @reviewer_backend (backend reviewer checks quality)
```

### Multiple Directives When Needed
If issue requires work from multiple roles:
```
Issue: [Backend + Frontend] User authentication

Work Items:
1. @engineer_backend - Implement login API endpoint
2. @engineer_frontend - Implement login form UI
3. @reviewer_backend - Review API endpoint
4. @reviewer_frontend - Review UI components
5. @qa - Test full login flow
```

## Issue Scope Requirements

### Issue Size: 15-20 Changes
- An "issue" should be completable in one PR
- Not so small it seems trivial (<5 changes)
- Not so large it requires multiple PRs (>50 changes)

### Issues Should Be Independent
- Can be reviewed independently
- Can be tested independently
- Don't require multiple unreleased PRs to complete

### When to Split
If issue exceeds 30 changes, split into:
- Issue A: Core functionality (<=20 changes)
- Issue B: Additional features or edge cases (<=20 changes)
- Document dependency: "Issue B depends on Issue A"

## Dependency Documentation

### Must Document

#### Blocking Dependencies (What this waits for)
```
This issue depends on:
- Issue BACK-123: User database schema (must complete first)
- Issue BACK-124: Authentication middleware (required)
- Library xyz v2.0: Already available
```

#### Blocked Dependencies (What waits for this)
```
This issue unblocks:
- Issue FRONT-045: Login page UI (waiting on API)
- Issue MOBILE-067: iOS login implementation (waiting on API)
```

#### No Circular Dependencies
- Issue A doesn't depend on B while B depends on A
- If circular dependency found, issue goes back for redesign

## Quality Gate Before Implementation

Issues meeting these criteria are **READY FOR IMPLEMENTATION**:

- [ ] Issue follows ABD template completely
- [ ] All sections filled out with sufficient detail
- [ ] Acceptance criteria are specific and testable
- [ ] Behavior specification is detailed enough to implement
- [ ] Technical approach is clear
- [ ] Risks are identified
- [ ] No ambiguities or open questions remain
- [ ] Single engineer unfamiliar with system could implement
- [ ] Architecture is sound (architect approved if needed)
- [ ] Dependencies are clear and met
- [ ] No circular dependencies
- [ ] Scope is 15-30 changes (not too small, not too large)
- [ ] Agent directive is specific
- [ ] Done checklist is realistic and verifiable

**Issues failing quality gate will not be assigned to engineers.**

## Issue Rejection Criteria

Issues will be sent back if:

- Missing any required section
- Acceptance criteria not specific/testable
- Behavior specification insufficient for implementation
- Ambiguous requirements or terms not defined
- Dependencies unclear or circular
- Technical approach not specified
- Scope too large (>40 changes) without splitting
- Scope too small (<5 changes) without justification
- Risks not documented
- Done checklist not specific/actionable
- No agent directive or not specific
- Contains contradictions or conflicts
- References non-existent issues or requirements
- Doesn't align with architecture guidelines

**Rejection feedback will specify exactly what's needed to make issue ready.**

---

These guidelines ensure issues are implementation-ready, preventing rework and miscommunication. Invest in quality issues; it saves significant time downstream.
