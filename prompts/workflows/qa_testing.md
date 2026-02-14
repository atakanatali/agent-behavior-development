# QA Testing Workflow

## Purpose
Validate that implementation matches specification, identify defects, and verify security and edge case handling before release.

## Input
- Pull request with code changes
- Original issue specification and acceptance criteria
- Reference to security_rules.md guardrails
- Test environment setup instructions
- Previous similar feature test results (for regression planning)

## Workflow Steps

### 1. Preparation & Planning
- Understand original specification completely
- Extract acceptance criteria: what must pass?
- Identify user flows affected
- Note any dependencies or prerequisite work
- Plan test environment setup

### 2. Test Case Development

Create test cases from acceptance criteria:

```
Acceptance Criterion: User can reset password via email link
Test Cases:
  TC-1: User receives password reset email with valid link
  TC-2: Link is valid for 24 hours
  TC-3: Link expires after 24 hours
  TC-4: User can set new password with valid requirements
  TC-5: User cannot reuse old password
  TC-6: Invalid link shows appropriate error
  TC-7: User receives confirmation email after reset
```

### 3. Functional Testing

#### Happy Path Testing
Follow the primary user flows:
- [ ] Primary user flow executes successfully
- [ ] Data is persisted correctly
- [ ] Success feedback is provided to user
- [ ] Expected state changes occur

Test the feature as a typical user would:
```
Test Flow: User Login
1. Open app
2. Click login button
3. Enter email: user@example.com
4. Enter password: (correct password)
5. Click submit
6. Verify: Redirected to home page
7. Verify: User profile shows correct user
8. Verify: Session token is set
```

#### Edge Case Testing
Test boundary conditions:

- Empty input: what happens with empty fields?
- Very long input: strings at or beyond max length
- Special characters: unicode, emoji, SQL characters
- Boundary values: min/max numbers, dates
- Null/undefined: missing optional fields
- Concurrent operations: simultaneous requests
- State transitions: unusual state combinations

Test examples:
```
Test Case: Maximum password length
1. Attempt to set password with 1000+ characters
2. Verify: System handles gracefully
3. Verify: Error message is clear if rejected

Test Case: Email with special characters
1. Try login with email: user+test@example.co.uk
2. Verify: Accepted and works correctly

Test Case: Rapid repeated requests
1. Click submit 5 times rapidly
2. Verify: Only one request processed
3. Verify: No duplicate actions
```

#### Error Scenario Testing
Test all documented error paths:

- Network error: simulate connection failure
- API error: simulate server error responses
- Invalid data: malformed responses
- Timeout: slow/hanging requests
- Partial failure: partial data success
- Missing data: expected data not present

Test examples:
```
Test Case: Network timeout during login
1. Start login request
2. Simulate network timeout (Proxy/Charles/Fiddler)
3. Verify: Timeout error shown to user
4. Verify: Login button re-enabled
5. Verify: User can retry

Test Case: Invalid API response
1. Login with mocked API returning invalid JSON
2. Verify: Parsing error handled gracefully
3. Verify: Error message shown to user
```

#### State Testing
Test state transitions:

- Initial state: first time user experience
- Populated state: with existing data
- Error state: from error recovery
- Transition state: during async operations

Test examples:
```
Test Case: Session expiration
1. Verify user is logged in
2. Wait for session timeout
3. Try to access protected feature
4. Verify: Redirected to login
5. Verify: Previous action lost

Test Case: Rapid state changes
1. Add item to cart
2. While network request in progress, add another
3. Verify: Both items added (no race condition)
```

### 4. Security Testing

#### Input Validation Testing
- [ ] XSS: try injecting `<script>alert('xss')</script>` in text fields
- [ ] SQL Injection: try injecting SQL in forms
- [ ] Command Injection: try shell commands
- [ ] Path Traversal: try ../ in file paths
- [ ] Type Mismatch: send wrong data types

Test examples:
```
Test Case: XSS Prevention in Comments
1. Submit comment with: <script>alert('xss')</script>
2. Verify: Script doesn't execute
3. Verify: HTML is escaped in display

Test Case: SQL Injection in Login
1. Email field: ' OR 1=1 --
2. Verify: Rejected or safely handled
3. Verify: Login fails with invalid creds
```

#### Authentication Testing
- [ ] Cannot access protected features without login
- [ ] Token/session validation working
- [ ] Token expiration handled
- [ ] Refresh token works
- [ ] Logout properly clears session

Test examples:
```
Test Case: Protected Route Access
1. Delete auth token from browser
2. Navigate to /dashboard
3. Verify: Redirected to login

Test Case: Token Expiration
1. Login successfully
2. Wait for token to expire (or mock expiration)
3. Try to fetch protected data
4. Verify: Get 401 Unauthorized
5. Verify: Redirected to login
```

#### Authorization Testing
- [ ] User can only access own data
- [ ] Admin-only endpoints reject regular users
- [ ] Role-based access controls enforced
- [ ] Data doesn't leak between users

Test examples:
```
Test Case: User A Cannot Access User B Data
1. Login as User A
2. Try to fetch User B's profile data
3. Verify: Forbidden (403) response
4. Verify: No data leaked

Test Case: Admin Endpoint Access
1. Login as regular user
2. Try to access /admin/users
3. Verify: Forbidden (403)
4. Login as admin
5. Verify: Access granted
```

#### Secrets & Sensitive Data
- [ ] No API keys in logs or responses
- [ ] No passwords returned in API
- [ ] Tokens not logged in plain text
- [ ] PII not exposed unnecessarily
- [ ] Sensitive data encrypted at rest and in transit

Test examples:
```
Test Case: No Secrets in Logs
1. Login successfully
2. Check browser console logs
3. Verify: No auth tokens logged
4. Check network tab
5. Verify: Password not sent as query param
```

### 5. Regression Testing

#### Existing Features Not Affected
- Test existing features that share code
- Verify no new bugs introduced
- Check related user flows still work

Test examples:
```
Regression Test: Login still works (even though added social login)
1. Login with email/password (existing flow)
2. Verify: Still works exactly as before

Regression Test: Profile page still works
1. Login
2. Navigate to profile
3. Verify: All existing data displays
4. Verify: No new errors
```

### 6. Performance Testing

#### Response Times
- [ ] API endpoints respond within expected time
- [ ] Pages load within acceptable time
- [ ] No noticeable lag or slowness
- [ ] Smooth animations (if applicable)

Test examples:
```
Test Case: Login Response Time
1. Click login
2. Measure time to success page
3. Verify: <2 second response time
4. Verify: No UI freezing
```

#### Load Impact
- [ ] Large datasets handled efficiently
- [ ] Long lists paginate or virtualize
- [ ] No memory leaks after repeated actions
- [ ] Battery impact acceptable (mobile)

Test examples:
```
Test Case: List with 1000 items
1. Load list with 1000 items
2. Verify: Pagination or virtualization
3. Verify: Scrolling smooth
4. Verify: No freezing or lag
```

### 7. Cross-Platform Testing (if applicable)

#### iOS Testing
- [ ] Feature works on iOS
- [ ] iPhone sizes supported
- [ ] iPad layout appropriate
- [ ] Keyboard handling correct
- [ ] Touch interactions work

#### Android Testing
- [ ] Feature works on Android
- [ ] Multiple device sizes tested
- [ ] Back button behavior correct
- [ ] System dialogs work
- [ ] Orientation changes handled

#### Browser Testing (Web)
- [ ] Chrome: works
- [ ] Firefox: works
- [ ] Safari: works
- [ ] Edge: works
- [ ] Mobile browsers: works

### 8. Accessibility Testing

#### Keyboard Navigation
- [ ] Tab order logical
- [ ] Enter submits forms
- [ ] Escape closes modals
- [ ] All interactive elements keyboard accessible

#### Screen Reader
- [ ] VoiceOver (iOS) works
- [ ] TalkBack (Android) works
- [ ] NVDA (Windows) works
- [ ] Content descriptions present

#### Visual
- [ ] Color contrast meets WCAG AA (4.5:1)
- [ ] Font sizes readable
- [ ] Spacing adequate
- [ ] Zoom to 200% works

### 9. Document Findings

#### Bug Report Format
```
BUG #1: Login button doesn't disable during request

Severity: Major (user can submit multiple times)

Repro Steps:
1. Open login page
2. Enter email: test@example.com
3. Enter password: password123
4. Click submit button rapidly
5. Observe: Button accepts multiple clicks

Expected: Button disabled during request
Actual: Button accepts 5 clicks, submits 5 times

Environment: Chrome 120, Windows 11
Screenshots: [attached]

Related Issues: [None]
```

#### Issue Categorization
- **Critical**: Blocking release, security risk, data loss
- **Major**: Significant feature impact, poor UX
- **Minor**: Cosmetic, workaround available
- **Suggestion**: Nice to have improvement

### 10. Provide Test Summary

```
## QA Testing Summary

### Feature: [Feature Name]
### Tested by: [QA Name]
### Date: [Date]
### Test Environment: [OS, Browser, App Version]

### Test Coverage
- Functional: 95% (9 of 10 flows tested)
- Security: 90% (9 of 10 vectors tested)
- Regression: 85% (7 of 8 affected features tested)
- Performance: Verified (response times <2s)
- Accessibility: WCAG AA compliant

### Results
- **Pass**: 45 test cases
- **Fail**: 2 critical issues
- **Blocked**: 0
- **Skipped**: 0 (note why if any)

### Issues Found
- Critical Issue 1: [Description]
- Critical Issue 2: [Description]
- Major Issue 1: [Description]

### Recommendation
**HOLD FOR FIXES** - Critical issues must be resolved before release

### Sign-off
- [ ] All critical issues resolved
- [ ] Regression tests pass
- [ ] Performance acceptable
- [ ] Ready for release
```

## Quality Checklist

- [ ] Acceptance criteria verified completely
- [ ] Happy path tested thoroughly
- [ ] Edge cases tested
- [ ] Error scenarios tested
- [ ] Security testing completed (OWASP)
- [ ] Authorization/authentication verified
- [ ] Regression testing completed
- [ ] Performance acceptable
- [ ] Cross-platform tested (if applicable)
- [ ] Accessibility verified
- [ ] All findings documented with repro steps
- [ ] Clear recommendation provided (pass/hold/fail)

## Escalation Points

Stop and escalate when:
- Security vulnerability found
- Critical issue found blocking feature
- Performance significantly worse than baseline
- Regression in critical existing feature
- Test environment not available or broken
- Requirements so vague testing strategy unclear
