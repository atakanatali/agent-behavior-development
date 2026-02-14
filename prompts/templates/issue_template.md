# ABD Issue Template

## Issue: [Agent Directive] [Title]

### Agent Directive
Specify which role should handle this issue:
- `@engineer_frontend` - React/Next.js implementation
- `@engineer_backend` - API/business logic implementation
- `@engineer_ios` - iOS/Swift implementation
- `@engineer_android` - Android/Kotlin implementation
- `@architect` - Architecture design/review work
- `@reviewer_frontend` - Frontend code review
- `@reviewer_backend` - Backend code review
- `@reviewer_ios` - iOS code review
- `@reviewer_android` - Android code review
- `@qa` - QA testing work

## Goal
One-sentence summary of what this issue accomplishes.

Example: "Implement user authentication with email/password login flow"

## Context

### Why does this issue exist?
- Business driver: Why is this important to users or the company?
- Feature alignment: How does this fit into the larger feature?
- Technical context: What systems does this touch?

### What does it depend on?
- List issues that must complete first
- List external dependencies (services, libraries, data)
- Are dependencies met? Ready to start?

### What depends on this?
- Which issues can't start until this is done?
- Which features are blocked by this?

## Acceptance Criteria

List specific, testable criteria that define "done":

- [ ] User can enter email and password in login form
- [ ] Password is validated: minimum 8 characters, at least one number
- [ ] Invalid credentials show error message
- [ ] Valid credentials create session and redirect to dashboard
- [ ] Invalid login attempts are logged with timestamp and IP
- [ ] Login form is responsive on mobile (320px+)
- [ ] Login page is accessible (WCAG AA)
- [ ] API response time <500ms under normal load
- [ ] No authentication tokens exposed in logs or responses

## Behavior Specification

Detailed description of what needs to be built. Include:
- User workflows and interactions
- System behaviors and state changes
- Edge cases and error handling
- Performance and scale considerations
- Security implications

### Primary User Flow
Step-by-step description of main flow:
1. User opens app/website
2. User clicks "Log In" button
3. User enters email: user@example.com
4. User enters password: (user types password)
5. User clicks "Sign In"
6. System validates credentials against database
7. System creates session token
8. System redirects to dashboard
9. User sees personalized dashboard

### Error Scenarios

#### Invalid Email Format
- If user enters: `notanemail`
- System should: Display error "Please enter a valid email"
- User should: See form ready for correction

#### Account Not Found
- If user enters: `new@example.com` (account doesn't exist)
- System should: Display generic error "Email or password incorrect"
- Rationale: Don't reveal which accounts exist
- Logging: Log attempt with timestamp, IP, email

#### Too Many Failed Attempts
- If user has 5 failed login attempts in 15 minutes
- System should: Lock account or rate limit
- User should: See message "Too many attempts. Try again in 15 minutes"
- Logging: Log lockout event with IP for security review

#### Expired Session
- If user's session token expires during active use
- System should: Catch 401 responses from API
- User should: Be redirected to login with message "Session expired"

### Edge Cases

#### Empty Fields
- If user clicks sign in with empty password
- Show error: "Password required"

#### Very Long Password (200+ characters)
- Accept and hash normally (no rejection needed)

#### Email with Special Characters
- Accept: user+test@example.co.uk
- Accept: user_name@example.com
- Handle correctly

#### SQL Injection Attempt
- If user enters: `' OR 1=1 --`
- System should: Use parameterized queries (no SQL injection)
- User should: See "Email or password incorrect"

#### XSS Attempt
- If user enters: `<script>alert('xss')</script>`
- System should: HTML-escape all inputs
- Script should not execute

### Performance Requirements
- API response time: <500ms at p95
- Page load time: <3 seconds
- Database query: <100ms for credential validation

### Security Requirements
- Password never sent in URL (POST request only)
- Password never logged in plain text
- Session tokens use secure, httpOnly cookies
- HTTPS required for all auth requests
- CSRF token required for login form

### Data Models

#### Login Request
```json
{
  "email": "user@example.com",
  "password": "securepassword123"
}
```

#### Login Response (Success)
```json
{
  "success": true,
  "user": {
    "id": "user_123",
    "email": "user@example.com",
    "name": "John Doe"
  },
  "session": {
    "token": "...",
    "expiresIn": 86400
  }
}
```

#### Login Response (Error)
```json
{
  "success": false,
  "error": "INVALID_CREDENTIALS",
  "message": "Email or password incorrect",
  "retryAfter": 0
}
```

## Technical Approach

### Architecture
- Pattern: [State management pattern used]
- Layer: [Which architectural layer(s) affected]
- Service: [Which service(s) updated]
- References: [Link to architecture docs if applicable]

### Database Changes (if applicable)
- No schema changes required (data already modeled)
- Or: "See issue BACK-123 for user table creation"

### API Changes (if applicable)
- Endpoint: POST /api/auth/login
- Request: See data models above
- Response: See data models above
- Status codes: 200 (success), 401 (invalid), 429 (rate limited), 500 (error)

### Frontend Implementation (if applicable)
- State management: Use Zustand for auth state
- Components: LoginForm, LoginPage
- Validation: Use react-hook-form with Zod schemas
- Error display: Show inline field errors and toast notifications

### Backend Implementation (if applicable)
- Endpoint: POST /api/auth/login in UserController
- Validation: Email format and password length checks
- Database: Query Users table by email
- Hashing: Use bcrypt to compare password
- Session: Create JWT token and set httpOnly cookie
- Logging: Log all login attempts (success and failure)

### Shared Code (if applicable)
- DTOs: LoginRequestDTO, LoginResponseDTO in /shared/dtos
- Validation: Email validation schema in /shared/validation

## Done Checklist

- [ ] Implementation complete per specification
- [ ] Unit tests written and passing
  - [ ] Valid login succeeds
  - [ ] Invalid email rejected
  - [ ] Invalid password rejected
  - [ ] XSS injection handled
  - [ ] SQL injection handled
- [ ] Integration tests written and passing
  - [ ] Full login flow works
  - [ ] Error responses correct
  - [ ] Session created properly
- [ ] Code review completed and approved
- [ ] QA testing completed and approved
  - [ ] Happy path tested
  - [ ] Error scenarios tested
  - [ ] Security tested
  - [ ] Performance verified
- [ ] Accessibility verified (WCAG AA)
- [ ] Documentation updated (if needed)
- [ ] Performance verified (response time <500ms)
- [ ] No security issues or hardcoded secrets
- [ ] Logging working and no sensitive data exposed

## Risks & Considerations

### Risk 1: Password Hashing Performance
- **Impact**: Slow login if hashing algorithm too slow
- **Mitigation**: Test bcrypt performance; consider tuning rounds
- **Owner**: Backend engineer to verify

### Risk 2: Session Token Expiration
- **Impact**: Users logged out unexpectedly if too short, security risk if too long
- **Mitigation**: Set 24-hour expiration with refresh token option
- **Owner**: Architect to finalize policy

### Risk 3: Rate Limiting Not Working
- **Impact**: Brute force attacks possible
- **Mitigation**: Implement rate limiting; test with stress tools
- **Owner**: QA to verify rate limiting

### Risk 4: Forgotten Session Cookie
- **Impact**: Feature shipped without auth working in some cases
- **Mitigation**: Double-check cookie is set; test in all browsers
- **Owner**: Frontend engineer to verify

### Consideration 1: Mobile App Compatibility
- Mobile apps can't use cookies; use token-based auth
- Consider device fingerprinting for enhanced security
- Test on actual iOS and Android devices

### Consideration 2: Third-Party Integration
- Currently no social login; plan for future OAuth integration
- Keep auth service loosely coupled for easy extension
- Document auth contracts for future integrations

## Related Issues
- Epic: FEAT-001 User Authentication
- Frontend: FRONT-045 (Login page UI)
- Backend: BACK-078 (User database schema)
- QA: QA-112 (Auth testing strategy)

## References
- [Authentication Best Practices Guide](https://example.com/docs/auth)
- [Security Rules](prompts/guardrails/security_rules.md)
- [Code Standards](prompts/guardrails/code_standards.md)

---

## Notes for Implementation

**For @engineer_backend:**
- Use bcrypt with 10+ rounds
- Implement rate limiting: 5 failed attempts per 15 minutes
- Add audit logging for all login attempts
- Return generic "Invalid credentials" error (don't reveal if email exists)

**For @engineer_frontend:**
- Show password strength indicator
- Disable button while request in progress
- Show clear error messages from API
- Test on iPhone SE, Galaxy S20, and desktop

**For QA:**
- Test on multiple devices and browsers
- Verify security scenarios (XSS, injection, rate limiting)
- Test edge cases (very long password, special characters)
- Load test: 100 concurrent login attempts
