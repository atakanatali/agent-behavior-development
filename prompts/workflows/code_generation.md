# Code Generation Workflow

## Purpose
Convert issue specifications into high-quality code changes that implement requirements while adhering to architectural and code standards.

## Input
- Issue with complete specification and acceptance criteria
- Reference to project_structure.md and architecture.md
- Reference to guardrails (code_standards.md, security_rules.md)
- Code review standards for the specific domain
- Context about what was tried before (if retrying after review feedback)

## Workflow Steps

### 1. Parse Issue Requirements
- Understand acceptance criteria completely
- Identify all edge cases and error scenarios
- Extract technical constraints and architecture patterns
- Note any performance or security requirements
- Understand dependencies and what's already available

### 2. Assess Implementation Approach
Before coding:

#### Design Phase
- Is the approach aligned with architecture?
- What design pattern applies? (MVVM, Repository, etc.)
- What's the data flow?
- What state needs to be managed?
- What errors can occur?

#### Testing Strategy
- What unit tests are needed?
- What integration tests?
- What edge cases must be tested?
- What security testing?

#### Performance Considerations
- Are there N+1 query risks?
- Should data be cached?
- Are there blocking operations?
- What's the complexity class?

### 3. Code Implementation

#### File Organization
- Follow project_structure.md
- Create new files if needed (justified)
- Organize into logical layers/components
- Group related code together

#### Code Style Consistency
- Match existing codebase patterns
- Follow language conventions (TypeScript, Kotlin, Swift, etc.)
- Use consistent naming: camelCase for functions, PascalCase for types
- Indent consistently (2 or 4 spaces as per team standard)

#### Implementation Quality

**Business Logic**
- SOLID principles applied
- DRY: no code duplication
- KISS: simple, readable implementations
- YAGNI: not building for hypothetical future

**Error Handling**
- All error paths handled
- Errors logged with context
- User-friendly error messages
- No silent failures

**Testing**
- Unit tests for business logic
- Integration tests for data flows
- Edge cases explicitly tested
- >80% code coverage minimum

**Logging & Observability**
- Structured logging with context
- Log at appropriate levels (DEBUG, INFO, WARN, ERROR)
- Never log sensitive data
- Enough logging to debug issues without being verbose

**Security**
- Input validation at boundaries
- No hardcoded secrets
- Authentication/authorization checks
- Injection prevention (SQL, XSS, etc.)

**Performance**
- No N+1 queries
- Async/await where needed
- No unnecessary copies or allocations
- Appropriate caching strategy

### 4. Code Changes Format

Output code changes as:

```
## File: [relative path]
ACTION: [create|modify|delete]

### Change 1: [Description]
[Code snippet or diff]

### Change 2: [Description]
[Code snippet or diff]
```

Example:
```
## File: src/services/UserService.ts
ACTION: create

### User service with authentication
```typescript
import { User } from '../models/User';
import { AuthProvider } from '../auth/AuthProvider';
import { Logger } from '../logging/Logger';

export class UserService {
  constructor(private authProvider: AuthProvider) {}

  async getCurrentUser(): Promise<User> {
    const token = this.authProvider.getToken();
    if (!token) {
      throw new Error('User not authenticated');
    }

    try {
      const response = await fetch('/api/users/me', {
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch user: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      Logger.error('Failed to get current user', { error });
      throw error;
    }
  }
}
```

## File: src/components/UserProfile.tsx
ACTION: modify

### Add user profile component using new service

[Before]
```typescript
export const UserProfile = () => {
  const [user, setUser] = useState(null);

  useEffect(() => {
    // Old inline fetch code
  }, []);

  return <div>{/* ... */}</div>;
};
```

[After]
```typescript
import { useQuery } from '@tanstack/react-query';
import { UserService } from '../services/UserService';

export const UserProfile = () => {
  const userService = new UserService(useAuthProvider());

  const { data: user, isLoading, error } = useQuery(
    ['user'],
    () => userService.getCurrentUser()
  );

  if (isLoading) return <LoadingSpinner />;
  if (error) return <ErrorMessage error={error} />;

  return (
    <div className="user-profile">
      <h1>{user.name}</h1>
      {/* ... */}
    </div>
  );
};
```
```

### 5. Testing Code

Write test code:

```
## File: src/services/UserService.test.ts
ACTION: create

### Unit tests for UserService
```typescript
import { UserService } from './UserService';
import { MockAuthProvider } from '../auth/MockAuthProvider';

describe('UserService', () => {
  it('should fetch current user successfully', async () => {
    const authProvider = new MockAuthProvider('valid-token');
    const service = new UserService(authProvider);

    global.fetch = jest.fn(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ id: '123', name: 'John' })
      })
    );

    const user = await service.getCurrentUser();

    expect(user.name).toBe('John');
  });

  it('should throw when user not authenticated', async () => {
    const authProvider = new MockAuthProvider(null);
    const service = new UserService(authProvider);

    await expect(service.getCurrentUser()).rejects.toThrow('not authenticated');
  });

  it('should throw on network error', async () => {
    const authProvider = new MockAuthProvider('valid-token');
    const service = new UserService(authProvider);

    global.fetch = jest.fn(() => Promise.reject(new Error('Network failed')));

    await expect(service.getCurrentUser()).rejects.toThrow('Network failed');
  });
});
```
```

### 6. Documentation

Document code:

```
## Documentation Updates

### src/services/README.md
ADD to Services section:

## UserService
Handles user-related API calls and state management.

Usage:
```typescript
const service = new UserService(authProvider);
const user = await service.getCurrentUser();
```

All methods require valid authentication token.
```
```

### 7. Self-Fix Context (if Retrying)

If this is a retry after code review feedback:

```
## Review Feedback Addressed

### Feedback 1: [Issue from review]
**Change**: [How it was fixed]
[Show the fix]

### Feedback 2: [Issue from review]
**Change**: [How it was fixed]
[Show the fix]
```

## Quality Checklist

- [ ] All acceptance criteria met
- [ ] Edge cases handled
- [ ] Error scenarios properly handled
- [ ] SOLID principles applied
- [ ] DRY: no code duplication
- [ ] Code follows project style conventions
- [ ] Tests written for business logic
- [ ] Tests passing locally
- [ ] No hardcoded secrets or configuration
- [ ] Input validation at boundaries
- [ ] Security implications considered
- [ ] Performance implications considered
- [ ] Logging adequate for debugging
- [ ] No N+1 queries (if database code)
- [ ] Async/await used appropriately
- [ ] Code is readable and maintainable
- [ ] Comments explain complex logic
- [ ] Documentation updated if needed

## Implementation Guidelines by Domain

### Frontend (React/Next.js)
- Components focused and reusable
- Proper state management (Context, Zustand, Redux)
- Responsive design tested on mobile
- Accessibility checked (a11y)
- Performance optimized (lazy loading, memoization)

### Backend (.NET/Node.js/Python)
- API design follows REST principles
- Database queries optimized
- Error handling comprehensive
- Logging structured and contextual
- Security checks in place

### iOS (Swift/SwiftUI)
- MVVM pattern applied
- Memory management sound
- Lifecycle properly managed
- SwiftUI best practices followed
- Accessibility considered

### Android (Kotlin/Compose)
- MVVM pattern applied
- Coroutines used correctly
- Lifecycle properly managed
- Compose best practices followed
- Material Design 3 applied

## Escalation Points

Stop and escalate when:
- Acceptance criteria can't be met with current design
- Architectural decision needed before implementation
- Performance requirements can't be met
- Security concern discovered during implementation
- Issue dependencies not met or unclear
