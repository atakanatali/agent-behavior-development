# Recycle Output Template

## Purpose
Summarize work outcomes at major handoff points (after code review, after QA, after architecture review) to capture what was kept, reused, or discarded, enabling the next phase to understand and build upon prior work effectively.

---

## Recycle Output: [Feature/PR Name]

**Date**: [YYYY-MM-DD]
**Transition**: [Code Generation → Code Review] OR [Code Review → QA] OR [QA → Architecture Review] OR [Architecture Review → Merge]
**From**: [previous agent role]
**To**: [next agent role]

---

## 🟢 Kept (Ready to Use)

Work that was approved and requires no changes.

### Code & Implementation
- [Specific file/module] - Approved as-is, no changes needed
  - Reason: [why it was kept]
  - Quality level: [exemplary / good / acceptable]

Example:
```
- src/services/AuthService.ts - Approved as-is
  - Reason: Security practices exemplary, bcrypt implementation correct
  - Quality level: Exemplary
  - Sign-off: Code reviewer approved 2024-01-15
```

### Architecture & Design
- [Design decision/pattern] - Approved and follows standards
  - Rationale: [why it's sound]
  - Reference: [architecture docs]

Example:
```
- JWT token session management - Approved
  - Rationale: Aligns with Modular Monolith pattern, good for scaling
  - Reference: prompts/guidelines/architecture.md (API design section)
  - Sign-off: Architect approved 2024-01-15
```

### Tests & Coverage
- [Test suite/area] - Comprehensive and sufficient
  - Coverage: [X%]
  - Notable tests: [specific scenarios]

Example:
```
- Authentication unit tests - Comprehensive
  - Coverage: 92% of AuthService
  - Notable tests: XSS injection, SQL injection, rate limiting verification
  - Sign-off: Code reviewer verified 2024-01-15
```

### Documentation
- [Documentation] - Complete and accurate
  - Format: [markdown/OpenAPI/etc]
  - Status: [ready to publish]

Example:
```
- API documentation (docs/api/auth.md) - Complete
  - Format: OpenAPI 3.0
  - Status: Ready to publish to developer docs
  - Sign-off: Architecture review confirmed accuracy
```

---

## 🟡 Reused (With Modifications)

Work from previous phase that was useful but required changes based on feedback.

### What Changed
- [Component/module] - Modified based on [reviewer] feedback
  - Original concern: [what was wrong]
  - Changes made: [specific modifications]
  - Files affected: [list files]

Example:
```
- AuthController.ts - Modified based on code review feedback
  - Original concern: Error messages leaked information (security issue)
  - Changes made: Returned generic "Invalid credentials" instead of "User not found" or "Password incorrect"
  - Files affected: src/controllers/AuthController.ts
  - Impact: More secure; maintains same functionality
```

### Reused Patterns
- [Pattern/approach] - Retained but enhanced
  - Original implementation: [what it was]
  - Enhancement: [how it was improved]

Example:
```
- Rate limiting middleware - Retained but enhanced
  - Original implementation: 5 failed attempts per 15 minutes
  - Enhancement: Added exponential backoff; first lockout 5 min, then 15 min, then 1 hour
  - Benefit: Better UX while maintaining security
```

### Lessons Applied
- [Learning point] - Applied from prior phases
  - Insight: [what was learned]
  - Application: [where/how it was used]

Example:
```
- Performance lessons from load testing - Applied to similar endpoints
  - Insight: N+1 queries cause 10-100x slowdown at scale
  - Application: Batch query pattern applied to user lookup + customer fetch
```

---

## 🔴 Banned (Rejected & Not Used)

Work from previous phase that was rejected and should not be used.

### Rejected Implementation
- [Component/module] - Rejected, complete rewrite needed
  - Reason for rejection: [why it didn't work]
  - What was tried: [original approach]
  - Why it failed: [specific issues]
  - Next approach: [what will be used instead]

Example:
```
- SessionService (original implementation) - Rejected
  - Reason: Did not handle concurrent requests properly
  - What was tried: Single-threaded session cache using Object
  - Why it failed: Race conditions detected in load testing; session could be corrupted
  - Next approach: Use Redis for concurrent-safe session store
```

### Rejected Patterns
- [Design pattern/approach] - Rejected, violates standards
  - Pattern attempted: [what was tried]
  - Why it was rejected: [standards violation or issues found]
  - Standard approach: [what should be used instead]

Example:
```
- Synchronous password validation - Rejected
  - Pattern attempted: bcrypt.compareSync() in request handler
  - Why rejected: Blocking operation blocks request handler (violates async-first principle)
  - Standard approach: Use async bcrypt.compare() to prevent blocking
```

### Rejected Architecture
- [Architecture decision] - Rejected, doesn't align with system
  - Proposed approach: [what was suggested]
  - Why rejected: [architectural conflicts]
  - Approved alternative: [what will be used]

Example:
```
- Distributed session store (separate service) - Rejected
  - Proposed approach: Create separate SessionService with its own database
  - Why rejected: Violates Modular Monolith pattern; creates unnecessary service boundary
  - Approved alternative: Use shared Redis instance within main service for sessions
```

---

## Summary Table

| Category | Item | Status | Notes |
|----------|------|--------|-------|
| Code | AuthService.ts | ✅ Kept | Exemplary security practices |
| Code | ErrorHandling | 🟡 Reused | Modified generic error messages |
| Design | JWT Sessions | ✅ Kept | Aligns with architecture |
| Design | Rate Limiting | 🟡 Reused | Enhanced with exponential backoff |
| Tests | Unit Tests | ✅ Kept | 92% coverage, comprehensive |
| Tests | Integration Tests | 🟡 Reused | Added edge case scenarios |
| Docs | API Docs | ✅ Kept | OpenAPI complete |
| Security | Password Hashing | 🟡 Reused | Changed from sync to async |
| Arch | Session Store | 🔴 Banned | Redis used instead of object cache |
| Performance | Query Optimization | ✅ Kept | Batch patterns applied |

---

## Knowledge Transfer

### For Next Phase
[Agent role or team receiving this work]

**Key understandings**:
- [Important insight 1 about how this system works]
- [Important insight 2 about why certain decisions were made]
- [Important insight 3 about risks or edge cases]

Example:
```
Key understandings for QA team:
1. Rate limiting is critical security feature - verify it activates after 5 failed attempts
2. Error messages intentionally generic ("Invalid credentials") - don't ask for better messages, this is intentional
3. bcrypt adds 100ms latency per login - this is expected and necessary for security; verify <500ms total response time
```

### Risks to Monitor
- [Risk 1] - How to detect, what to do if it occurs
- [Risk 2] - How to detect, what to do if it occurs

Example:
```
Risks to monitor in production:
1. Concurrent session corruption - Monitor for duplicate/conflicting session tokens; if detected, invalidate and require re-login
2. Rate limiting too aggressive - Monitor if legitimate users getting locked out; adjust thresholds if >0.1% false positive rate
```

### Questions for Next Phase
- [Question 1] - What should be tested/verified next
- [Question 2] - What assumptions should be validated

Example:
```
Questions for QA:
1. Should password reset link work for expired tokens, or should it require fresh request?
2. What's the business rule on mobile app login - should sessions sync across devices, or be device-specific?
```

---

## Handoff Checklist

Before passing to next phase, confirm:

- [ ] All "Kept" work is documented with sign-offs
- [ ] All "Reused" work has clear change tracking
- [ ] All "Banned" work is justified with clear reasons
- [ ] Knowledge transfer section completed
- [ ] Risks identified and documented
- [ ] Open questions for next phase listed
- [ ] All files and artifacts referenced are current
- [ ] No blocking issues remain
- [ ] Previous phase fully understands what to do next

---

## Example: Full Recycle Output

### Recycle Output: User Authentication Feature

**Date**: 2024-01-20
**Transition**: Code Review → QA Testing
**From**: Senior Backend Engineer
**To**: QA Testing Team

---

## 🟢 Kept (Ready to Use)

### Code & Implementation
- **src/services/AuthService.ts** - Approved as-is
  - Reason: Security practices exemplary; bcrypt implementation correct; test coverage 92%
  - Quality level: Exemplary
  - Sign-off: @reviewer_backend approved 2024-01-18
  - Details: Password validation logic correct, rate limiting functional, error handling comprehensive

- **src/controllers/AuthController.ts** - Approved as-is
  - Reason: Error handling prevents information leakage; proper HTTP status codes
  - Quality level: Good
  - Sign-off: @reviewer_backend approved 2024-01-18
  - Details: Uses parameterized queries for SQL injection prevention

### Tests & Coverage
- **AuthService unit tests** - Comprehensive and sufficient
  - Coverage: 92% of critical paths
  - Notable tests: XSS injection, SQL injection, rate limiting, password validation
  - 25 test cases covering happy path, edge cases, error scenarios
  - Sign-off: Code reviewer verified 2024-01-18

---

## 🟡 Reused (With Modifications)

### What Changed
- **Error messages** - Modified for security
  - Original concern: Returned "User not found" vs "Password incorrect" (information leakage)
  - Changes made: Generic "Email or password incorrect" for all invalid credential scenarios
  - Files affected: src/controllers/AuthController.ts (lines 45-68)
  - Impact: More secure; prevents account enumeration attacks
  - Tested by: Code reviewer, approved 2024-01-18

- **Password validation** - Modified to async
  - Original concern: Using bcrypt.compareSync() blocked request handler
  - Changes made: Changed to async bcrypt.compare() with proper await
  - Files affected: src/services/AuthService.ts (lines 34-42)
  - Impact: Non-blocking; improved performance under load
  - Performance impact: Same total time, but request handler not blocked
  - Tested by: Code reviewer, performance test passed 2024-01-18

### Reused Patterns
- **Rate limiting middleware** - Retained from design, no changes
  - Implementation: 5 failed attempts per 15 minutes per IP
  - Testing needed: QA to verify lockout behavior and error messages

### Lessons Applied
- **Input validation** - Applied rigorously
  - Insight: One SQL injection vulnerability found in design phase
  - Application: All inputs validated at API boundary; parameterized queries used everywhere
  - Result: Code reviewer approved as secure

---

## 🔴 Banned (Rejected & Not Used)

### Rejected Implementation
- **Original in-memory session cache** - Rejected, replaced with Redis
  - Reason: Not thread-safe; concurrent requests could corrupt sessions
  - What was tried: Using JavaScript Object as cache with simple get/set
  - Why it failed: Load testing revealed race conditions; under 100 concurrent requests, ~5% of sessions corrupted
  - Next approach: Redis for concurrent-safe session store (separate issue created)
  - Status: Held for follow-up work to prevent blocking current feature

- **Synchronous password hashing** - Rejected in code review
  - What was tried: bcrypt.compareSync() for simplicity
  - Why rejected: Violates async-first architecture principle; blocks request handler
  - Changed to: bcrypt.compare() with async/await
  - Impact: Code review feedback incorporated immediately

---

## Summary Table

| Item | Status | Notes |
|------|--------|-------|
| AuthService.ts | ✅ Kept | Security exemplary, comprehensive tests |
| AuthController.ts | ✅ Kept | Error handling prevents info leakage |
| Error messages | 🟡 Modified | Generic messages prevent account enumeration |
| Password validation | 🟡 Modified | Changed to async to prevent blocking |
| Rate limiting | ✅ Kept | Ready for QA testing |
| Unit tests | ✅ Kept | 92% coverage, 25 test cases |
| In-memory cache | 🔴 Banned | Not thread-safe; Redis planned |

---

## Knowledge Transfer for QA

### Key Understandings
1. **Rate limiting is critical** - Verify it activates after exactly 5 failed attempts per IP, blocks for 15 minutes
2. **Error messages intentionally generic** - "Email or password incorrect" for all invalid credential scenarios is intentional (security)
3. **Performance impact** - bcrypt adds ~100ms per login (expected for security); total response time should be <500ms
4. **Security design** - Password never logged, tokens in httpOnly cookies only, HTTPS required
5. **Concurrency** - Currently using Node.js single-threaded model; future Redis sessions will enable horizontal scaling

### Risks to Monitor
1. **Rate limiting too aggressive** - Monitor for legitimate users locked out; threshold may need tuning for user experience
   - How to detect: Error logs showing lockouts from legitimate IPs
   - Action if detected: Adjust 5-attempt threshold or 15-minute window
2. **Session corruption** - Currently possible with in-memory cache under high load
   - How to detect: Users logged out unexpectedly, duplicate sessions
   - Action if detected: Already known; Redis migration will fix; use this version for moderate load only
3. **Brute force attacks** - Rate limiting should prevent, but verify
   - How to detect: Error logs showing attack patterns
   - Action if detected: Escalate to security team; may need additional captcha

### Questions for QA
1. **Test scope**: Should QA test all 5 failed attempts manually, or can automated test do this?
2. **Load testing**: What's expected concurrent load? (Load tested to 100, but production may differ)
3. **Mobile apps**: Do mobile apps get same rate limiting, or different policy?
4. **Refresh flow**: If token expires mid-session, does user get smooth re-auth or hard logout?

---

## Handoff Checklist

- [x] All "Kept" work documented with sign-offs
- [x] All "Reused" work has clear change tracking
- [x] All "Banned" work justified with clear reasons
- [x] Knowledge transfer section completed
- [x] Risks identified and documented
- [x] Open questions for next phase listed
- [x] All files referenced are current (as of 2024-01-20)
- [x] No blocking issues remain (in-memory cache issue is tracked separately)
- [x] Previous phase understands what to do next (comprehensive test plan)

---

## Sign-Off

**From**: @engineer_backend (Code Generation)
**To**: @qa (QA Testing Phase)
**Date**: 2024-01-20
**Status**: Ready for QA Testing ✓

All code approved, security verified, performance tested. Ready for comprehensive QA validation.

---
