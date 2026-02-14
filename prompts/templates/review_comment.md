# ABD Review Comment Template

## Structure for Constructive Feedback

### Format 1: Blocking Issue

```
## 🚫 [BLOCKING] Issue Title

**Location**: [filename]:[line number]

**Issue**: [Clear description of the problem]

[Example code or context]

**Why this matters**: [Explain impact and importance]

**Suggested fix**: [Specific suggestion for resolution]

```typescript
// Before (current code)
const user = Users.find(id => id == userId);

// After (suggested fix)
const user = Users.find(id => id === userId);
```

**Verification**: [How to verify the fix is correct]

---

### Example: Blocking Issue (Security)

```
## 🚫 [BLOCKING] SQL Injection Vulnerability

**Location**: src/repositories/UserRepository.ts:45

**Issue**: This query is vulnerable to SQL injection. The email parameter is concatenated directly into the SQL string instead of using parameterized queries.

[Code snippet showing vulnerability]

**Why this matters**: An attacker can inject SQL commands through the email field, potentially accessing or modifying all user data. This is a critical security vulnerability that must be fixed before merge.

**Suggested fix**: Use parameterized queries with placeholders:

```typescript
// Before (vulnerable)
const user = await db.query(
  `SELECT * FROM users WHERE email = '${email}' AND status = '${status}'`
);

// After (secure)
const user = await db.query(
  'SELECT * FROM users WHERE email = ? AND status = ?',
  [email, status]
);
```

**Verification**: Test with email value: `' OR 1=1 --` and verify no rows returned (or only intended rows if that's the goal).

---
```

### Format 2: Major Issue

```
## ⚠️ [MAJOR] Issue Title

**Location**: [filename]:[line number]

**Issue**: [Description of concern]

**Impact**: [How this affects code quality, performance, maintainability]

**Recommendation**: [Suggested approach to address]

```

### Example: Major Issue (Performance)

```
## ⚠️ [MAJOR] N+1 Query Problem

**Location**: src/services/UserService.ts:78

**Issue**: This code fetches a list of orders and then loops through each order to fetch the customer. This creates N+1 queries (1 for orders + 1 for each order's customer).

```typescript
// Current code (N+1 problem)
const orders = await db.orders.find({ status: 'pending' });

const enriched = orders.map(order => {
  const customer = await db.customers.find({ id: order.customerId });
  return { ...order, customer };
});
```

**Impact**: Performance will degrade significantly as data grows. With 10,000 orders, this creates 10,001 database queries instead of 2. Estimated 50-100x slower.

**Recommendation**: Fetch all customers in a single batch query:

```typescript
// Better approach (batch query)
const orders = await db.orders.find({ status: 'pending' });
const customerIds = orders.map(o => o.customerId);
const customers = await db.customers.whereIn('id', customerIds);

const customerMap = new Map(customers.map(c => [c.id, c]));
const enriched = orders.map(order => ({
  ...order,
  customer: customerMap.get(order.customerId)
}));
```

**References**: See code_standards.md for performance guidelines.

---
```

### Format 3: Suggestion

```
## 💡 [SUGGESTION] Idea for Improvement

**Location**: [filename]:[line number]

**Suggestion**: [Optional improvement idea]

**Rationale**: [Why this might be better, but not required]

```

### Example: Suggestion

```
## 💡 [SUGGESTION] Extract Duplicate Validation Logic

**Location**: src/controllers/UserController.ts

**Suggestion**: The email validation logic appears in both LoginController (line 45) and SignupController (line 120). Consider extracting to a shared validator:

```typescript
// Create src/validators/EmailValidator.ts
export const validateEmail = (email: string): ValidationResult => {
  if (!email) return { valid: false, error: 'Email required' };
  if (!email.includes('@')) return { valid: false, error: 'Invalid email' };
  return { valid: true };
};

// Then use in both controllers
const validation = validateEmail(email);
if (!validation.valid) return error(validation.error);
```

**Rationale**: Eliminates duplication, makes validation changes centralized, ensures consistency across the app. But this can be addressed in a follow-up refactoring if you prefer to merge this PR as-is.

---
```

### Format 4: Question for Clarification

```
## ❓ [QUESTION] Need Clarification

**Location**: [filename]:[line number]

**Question**: [What you're unclear about]

**Context**: [Why you're asking]

```

### Example: Question

```
## ❓ [QUESTION] Why Use setTimeout Instead of Promise?

**Location**: src/services/NotificationService.ts:34

**Question**: Why is setTimeout used here instead of returning a Promise that resolves after the delay?

```typescript
// Current approach
setTimeout(() => {
  console.log('Retry after 5 seconds');
}, 5000);

// Alternative approach
await new Promise(resolve => setTimeout(resolve, 5000));
```

**Context**: The setTimeout approach makes testing harder and doesn't play well with async/await patterns. Understanding the reasoning would help me provide better feedback.

---
```

### Format 5: General Comments (Non-Issue)

```
## 👍 [COMMENT] General Observation

[Positive feedback or informational observation]

```

### Example: General Comment

```
## 👍 [COMMENT] Great Error Handling

I really like how you structured the error handling in the retry logic. Using specific error types and clear logging makes debugging much easier. This is a pattern we should use more widely.

---
```

## Review Comment Best Practices

### Do:
- ✅ Be specific: reference lines, provide examples
- ✅ Explain the "why": help the author learn
- ✅ Suggest solutions: if you see a problem, propose a fix
- ✅ Be respectful: assume good intent
- ✅ Acknowledge good work: praise when you see it
- ✅ Separate blocking from optional feedback

### Don't:
- ❌ Be vague: "this is bad" without explanation
- ❌ Be condescending: avoid "obviously" or "anyone would know"
- ❌ Demand perfection: distinguish between blocking and nice-to-have
- ❌ Ignore positive work: give credit
- ❌ Make it personal: focus on code, not the person
- ❌ Pile on feedback: consolidate related comments

## Review Comment Examples by Scenario

### Security Issue Found

```
## 🚫 [BLOCKING] Missing Input Validation

**Location**: src/api/routes/users.ts:23

**Issue**: The endpoint accepts user input directly without validation. An attacker could send 10,000 character strings where we expect names (which should be <100 chars), causing storage issues or DoS.

**Current code**:
```javascript
app.post('/api/users', (req, res) => {
  const user = { name: req.body.name, email: req.body.email };
  db.save(user);
});
```

**Fix**: Add validation middleware or schema validation:

```javascript
app.post('/api/users', validateInput, (req, res) => {
  // validated input available as req.validated
});

// Or use Zod/Joi
const userSchema = z.object({
  name: z.string().max(100),
  email: z.string().email()
});

const validated = userSchema.parse(req.body); // Throws if invalid
```

**Why it matters**: Protecting against injection and DoS attacks is critical for production apps.

---
```

### Performance Issue Found

```
## ⚠️ [MAJOR] Memory Leak in Event Listener

**Location**: src/components/DataViewer.tsx:45

**Issue**: The event listener is registered in useEffect but never cleaned up. This causes multiple listeners to accumulate each time the component re-renders, consuming memory and causing duplicate events.

```javascript
// Current code (leaks listeners)
useEffect(() => {
  window.addEventListener('scroll', handleScroll);
}, []); // Missing cleanup!

// Fixed code
useEffect(() => {
  window.addEventListener('scroll', handleScroll);
  return () => window.removeEventListener('scroll', handleScroll); // Cleanup
}, []);
```

**Testing**:
1. Open DevTools Memory tab
2. Record heap snapshot
3. Scroll a few times
4. Record another snapshot
5. Compare - with bug you'll see event listeners growing

**Impact**: Users on low-memory devices (older phones, constrained environments) will experience slowdowns or crashes.

---
```

### Code Style Issue

```
## 💡 [SUGGESTION] Use Consistent Quote Style

**Location**: src/config.ts

**Observation**: The file mixes single and double quotes. Consider using consistent quotes (project standard is single quotes) for readability:

```javascript
// Currently mixed
const config = {
  apiUrl: 'https://api.example.com',
  timeout: "5000",  // ← double quotes inconsistent
  debug: 'true'
};

// After fix
const config = {
  apiUrl: 'https://api.example.com',
  timeout: '5000',
  debug: 'true'
};
```

**Note**: This is a minor style issue and can be addressed in follow-up, but we generally keep consistent styling in files.

---
```

### Architectural Concern

```
## ⚠️ [MAJOR] Architectural Violation: Direct Service Coupling

**Location**: src/features/UserProfile/UserProfileComponent.tsx:12

**Issue**: This component directly imports and uses UserService, creating tight coupling. Per our architecture guidelines, components should use dependency injection or context for services.

```typescript
// Current (tight coupling)
import { UserService } from '../../services/UserService';

export const UserProfile = () => {
  const service = new UserService(); // Creates dependency directly
  // ...
};

// Better approach (dependency injection)
export const UserProfile = ({ userService }: { userService: UserService }) => {
  // ...
};

// Or use context (if shared across many components)
const userService = useContext(UserServiceContext);
```

**Why it matters**: Direct service creation makes testing difficult and breaks the dependency inversion principle. It also makes it hard to swap implementations for testing or future changes.

**Reference**: See prompts/guidelines/architecture.md section on dependency injection.

---
```

## Review Decision Statements

### When Approving
```
## ✅ Approved

This PR is ready to merge. Code quality is excellent, tests are comprehensive, and it meets all acceptance criteria. Great work!

No changes needed.
```

### When Requesting Changes
```
## 🔄 Request Changes

This PR needs to address the blocking issues listed above before it can be merged:

1. Fix SQL injection vulnerability (line 45)
2. Add missing password validation (line 78)

Once these are addressed, we can do another quick review. The rest of the code looks good!
```

### When Holding for Discussion
```
## 🤔 Hold for Discussion

Before approving, I'd like to discuss the architectural approach for token refresh. Current approach uses localStorage, but there are security tradeoffs. Let's sync on this before proceeding.

Not blocking other work, but should discuss this with the team.
```

---
