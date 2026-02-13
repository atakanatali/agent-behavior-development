# Code Quality Standards

Standards that all code must meet across frontend, backend, iOS, and Android domains.

## SOLID Principles (Mandatory for All Domains)

### Single Responsibility Principle (SRP)
- **Rule**: Each class, function, or component should have ONE reason to change
- **Application**:
  - Frontend: Components do presentation logic only; business logic in services
  - Backend: Controllers handle HTTP; Services handle business logic; Repositories handle data access
  - iOS: ViewModels handle state; Views do presentation; Models represent data
  - Android: ViewModels handle state; Composables do presentation; Repositories handle data

- **Good Example**: UserService only handles user-related operations
- **Bad Example**: UserService that also handles logging, caching, and email sending

### Open/Closed Principle (OCP)
- **Rule**: Classes open for extension, closed for modification
- **Application**:
  - Use interfaces/protocols for abstraction
  - Use inheritance/composition over editing existing code
  - Use adapters for new capabilities

- **Good Example**: Logger interface with Console and File implementations
- **Bad Example**: Add more if-statements to existing Logger class for each new log type

### Liskov Substitution Principle (LSP)
- **Rule**: Subclasses must be substitutable for base classes
- **Application**:
  - If function expects Logger, any Logger subtype must work
  - Override methods must maintain contracts
  - No surprises in derived implementations

### Interface Segregation Principle (ISP)
- **Rule**: Don't force clients to depend on interfaces they don't use
- **Application**:
  - Small, focused interfaces preferred over large ones
  - Implement only what's needed
  - Avoid "fat" interfaces

### Dependency Inversion Principle (DIP)
- **Rule**: Depend on abstractions, not concrete implementations
- **Application**:
  - Use interfaces/protocols for dependencies
  - Inject dependencies rather than creating them
  - No hardcoded service creation

## DRY (Don't Repeat Yourself)

- **Rule**: Write code once; reuse everywhere
- **Application**:
  - Extract duplicated logic into shared functions
  - Use constants for repeated values
  - Extract common patterns into utilities

- **Maximum Duplication**: Duplicate code twice before extracting (rule of three)
- **Exception**: Code is similar but different enough that extraction creates complexity
  - In that case, document why and revisit if patterns emerge

## KISS (Keep It Simple, Stupid)

- **Rule**: Simplest solution that works is best
- **Application**:
  - Don't over-engineer; solve the actual problem
  - Readable code is better than clever code
  - Magic numbers become named constants
  - Complex logic has comments explaining intent

- **Example**: Use if-statement instead of ternary if code is more readable

## YAGNI (You Aren't Gonna Need It)

- **Rule**: Don't build for future features that haven't been requested
- **Application**:
  - Don't create "generic" solutions for hypothetical cases
  - Implement what's specified, not what might be useful someday
  - Refactor when requirements change, not in anticipation

## Naming Conventions

### General Rules
- **Self-documenting**: Names should explain purpose without comment needed
- **Avoid abbreviations**: `getUserList()` not `getUL()`
- **Avoid single letters** (except `i` in loops, `e` in exceptions): `for (int i = 0; ...)`
- **Avoid pronouns**: `getName()` not `getIt()`
- **Boolean names**: `isActive`, `hasPermission`, `canDelete`

### Language-Specific

**TypeScript/JavaScript**:
- Functions: camelCase - `getUserById()`, `calculateTotal()`
- Classes: PascalCase - `UserService`, `OrderRepository`
- Constants: UPPER_SNAKE_CASE - `MAX_RETRY_COUNT`, `API_ENDPOINT`
- Private members: prefix with `_` - `_internalState`

**Swift**:
- Functions: camelCase - `getUserById()`, `calculateTotal()`
- Types: PascalCase - `UserService`, `NetworkRequest`
- Constants: camelCase or PascalCase - `maxRetryCount`, `DefaultTimeout`
- Private members: prefix with `_` or mark `private`

**Kotlin**:
- Functions: camelCase - `getUserById()`, `calculateTotal()`
- Classes: PascalCase - `UserService`, `NetworkRequest`
- Constants: UPPER_SNAKE_CASE - `MAX_RETRY_COUNT`, `DEFAULT_TIMEOUT`
- Private members: prefix with `_` or mark `private`

## Function/Method Design

### Size & Complexity
- **Maximum length**: 50 lines of code (excluding comments/blank lines)
- **Maximum nested depth**: 3 levels
- **Maximum parameters**: 3 (use object/struct for more)
- **Maximum cyclomatic complexity**: 10 (number of decision branches)

### Naming
- **Verb for action**: `fetchUser()`, `validateEmail()`, `convertToDTO()`
- **Predicate for boolean**: `isValid()`, `hasPermission()`, `canAccess()`
- **Clear intent**: `calculateTotalPrice()` not `compute()`, `calcPrce()`

### Parameters
- **Order matters**: Related parameters together
- **Avoid boolean parameters**: Use enum or separate functions
- **Use objects for multiple parameters** (>3):
  ```typescript
  // Bad
  function createUser(name, email, age, address, phone, company) { }

  // Good
  function createUser(userDetails: UserCreateRequest) { }
  ```

## Error Handling

### General Rules
- **No silent failures**: Always log or throw
- **Specific error types**: Not generic Exception/Error
- **Context in errors**: Include what operation failed, what data, what was expected
- **User-friendly messages**: Don't expose internals to users

### Catching Errors
```typescript
// Good: Specific error catching
try {
  await fetchUser(id);
} catch (error) {
  if (error instanceof NetworkError) {
    // Handle network specifically
  } else if (error instanceof ValidationError) {
    // Handle validation specifically
  } else {
    throw error; // Re-throw if unexpected
  }
}

// Bad: Catching everything
try {
  await fetchUser(id);
} catch (error) {
  console.log('Something went wrong');
}
```

### Logging with Context
```typescript
// Good: Context included
logger.error('Failed to create user', {
  error: error.message,
  userId: user.id,
  timestamp: new Date().toISOString(),
  requestId: context.requestId
});

// Bad: No context
logger.error('Error creating user');
```

## Performance Standards

### No N+1 Queries
```typescript
// Bad: N+1 problem
const orders = await db.orders.find();
const enriched = orders.map(async order => {
  const customer = await db.customers.find({ id: order.customerId }); // 1 + N queries
  return { ...order, customer };
});

// Good: Batch query
const orders = await db.orders.find();
const customerIds = orders.map(o => o.customerId);
const customers = await db.customers.whereIn('id', customerIds); // 2 queries
```

### Async/Await Everywhere
- **No blocking operations** in request handlers
- **No synchronous I/O**: All I/O must be async
- **Proper error propagation**: Await and catch, don't ignore

### Caching Strategy
- **Identify cached data**: What data changes slowly?
- **Set TTL**: Cache invalidation strategy
- **Invalidate on mutations**: Update or delete clears cache
- **Never cache user-specific data** without proper scoping

## Memory Management

### TypeScript/JavaScript
- **No memory leaks**: All listeners/subscriptions cleaned up
- **Unsubscribe in cleanup**: `useEffect` return function or component destructor
- **No circular references**: Objects referencing each other through closures

### Swift
- **No retain cycles**: Use `weak` for backreferences
- **Unsubscribe properly**: Cancel subscriptions in deinit
- **Image/data cleanup**: Release large objects when done

### Kotlin
- **Lifecycle-aware**: Subscriptions scoped to component lifecycle
- **Coroutine scopes**: Use proper scope (activity, fragment, viewmodel)
- **Memory leaks**: Test with LeakCanary in debug

## Testing Standards

### Unit Tests
- **Test business logic**: Pure functions and methods
- **Test edge cases**: Empty, null, boundaries, max values
- **Test error paths**: All exceptions and error conditions
- **Test one thing**: Each test verifies one behavior

### Test Organization
```typescript
describe('UserService', () => {
  describe('createUser', () => {
    it('should create user with valid data', () => { });
    it('should throw on invalid email', () => { });
    it('should throw on duplicate email', () => { });
  });
});
```

### Integration Tests
- **Test workflows**: Happy path and error scenarios
- **Test data persistence**: Verify data saved correctly
- **Test API contracts**: Request/response match spec
- **Test with real DB**: Use test database, not mocks (for integration)

### Coverage Requirements
- **Minimum**: 80% of new code
- **Critical paths**: 100% coverage of business logic
- **Ignore**: Trivial getters/setters, generated code, UI rendering

## Logging Standards

### Structured Logging Required
```typescript
// Good: Structured
logger.info('User login successful', {
  userId: user.id,
  email: user.email,
  loginMethod: 'password',
  ipAddress: request.ip
});

// Bad: Unstructured string
logger.info(`User ${user.email} logged in from ${request.ip}`);
```

### Log Levels
- **DEBUG**: Detailed diagnostic information (variable values, flow)
- **INFO**: Informational messages (significant events, state changes)
- **WARN**: Warning messages (deprecated APIs, recoverable errors)
- **ERROR**: Error messages (failures that don't stop application)
- **FATAL**: Critical errors (application must stop)

### Never Log Sensitive Data
- **No passwords, tokens, API keys**
- **No credit card numbers, SSN, PII**
- **No personal information** unless anonymized
- **Mask sensitive parts**: "email: user****@example.com"

## Code Organization

### File Structure
- **One type/class per file** (except related tiny types)
- **Logical grouping**: Related code together
- **Consistent naming**: File names match contents
- **Avoid deep nesting**: Maximum 3-4 directory levels

### Imports/Exports
- **Named exports preferred**: More explicit
- **Avoid circular dependencies**: Can hide design issues
- **Group imports**: Standard library, external packages, internal code

## Comments & Documentation

### Good Comments Explain "Why"
```typescript
// Good: Explains decision
// Using bcrypt with 10 rounds: higher for security, lower for UX
// 10 rounds: ~100ms hashing time (acceptable trade-off)
const saltRounds = 10;

// Bad: Restates code
// Increment counter
counter++;
```

### JSDoc/KDoc for Public APIs
```typescript
/**
 * Fetches a user by ID from the database.
 * @param id - The user's unique identifier
 * @returns Promise resolving to User object or null if not found
 * @throws {DatabaseError} If database query fails
 * @example
 * const user = await userRepository.findById('user_123');
 */
async function findById(id: string): Promise<User | null> {
  // ...
}
```

### Complex Logic Needs Explanation
- Document assumptions
- Explain tradeoffs if non-obvious
- Reference external resources if applicable
- Explain what's intentional (like performance optimization)

## No Hardcoded Values

### Use Constants
```typescript
// Bad: Magic numbers
if (attempts > 5) { // What is 5?
  setTimeout(() => { }, 15 * 60 * 1000); // What is 15*60*1000?
}

// Good: Named constants
const MAX_LOGIN_ATTEMPTS = 5;
const LOCKOUT_DURATION_MS = 15 * 60 * 1000;
if (attempts > MAX_LOGIN_ATTEMPTS) {
  setTimeout(() => { }, LOCKOUT_DURATION_MS);
}
```

### Configuration from Environment
```typescript
// Bad: Hardcoded
const apiUrl = 'https://api.example.com';

// Good: Environment variable
const apiUrl = process.env.API_URL || 'https://api.example.com';
```

## Null/Undefined Handling

### Null Safety (TypeScript)
```typescript
// Bad: Assumes exists
const name = user.profile.name.toUpperCase();

// Good: Null checks
const name = user?.profile?.name?.toUpperCase() ?? 'Unknown';

// Good: Explicit handling
if (!user || !user.profile || !user.profile.name) {
  return 'Unknown';
}
const name = user.profile.name.toUpperCase();
```

### Defaults and Guards
```typescript
// Good: Default values
function greet(name = 'Guest') {
  return `Hello, ${name}`;
}

// Good: Guard clauses
function processUser(user) {
  if (!user) return null;
  if (!user.isActive) return null;
  // Process active user
}
```

---

These standards apply universally. No exceptions for time pressure, complexity, or domain. Domain reviewers enforce these standards consistently.
