# Task Distribution Workflow

## Purpose
Map issues to engineer agents by domain, define execution order, and identify dependencies to enable parallel execution.

## Input
- Enriched technical design with domain-labeled issues
- Prompts/personas directory (engineer roles available)
- Team capacity and availability constraints (if applicable)

## Workflow Steps

### 1. Categorize Issues by Primary Domain
Group issues by agent responsibility:

**Frontend issues** → @engineer_frontend
- React/Next.js components
- Client-side state management
- UI interactions and flows
- Responsive design implementation

**Backend issues** → @engineer_backend
- API endpoint implementation
- Business logic
- Database operations and migrations
- Service-to-service communication

**iOS issues** → @engineer_ios
- SwiftUI screens and components
- iOS-specific business logic
- Core Data operations
- iOS network layer

**Android issues** → @engineer_android
- Jetpack Compose screens
- Android-specific business logic
- Room database operations
- Android network layer

**Shared/Infrastructure issues** → @engineer_backend (or shared team)
- Shared DTOs and contracts
- Database schema (if backend-primary)
- Infrastructure and deployment
- Authentication/authorization layer

**Architectural issues** → @architect
- New service boundaries
- Architecture pattern implementation
- Cross-cutting concerns
- Infrastructure design

### 2. Identify Issue Dependencies
For each issue, determine:

#### Blocking Dependencies
- What must complete before this can start?
- Which other issues does this need to wait for?
- What external dependencies exist?

#### Parallel Work
- What issues can run concurrently?
- Which issues have no dependencies?

Create dependency map:
```
Frontend Component Issue
  ↓ depends on
Backend API Issue
  ↓ depends on
Database Migration Issue
```

### 3. Identify Critical Path
- Find the longest chain of dependencies
- These issues should be prioritized
- Flag if critical path is too long

### 4. Optimize Execution Sequence

#### Phase 1: Foundation (Zero Dependencies)
Issues with no dependencies or only shared library dependencies:
- Shared DTOs and contracts
- Database schema changes
- Authentication layer updates
- Base infrastructure

#### Phase 2: APIs and Core Logic
Issues that depend on Phase 1:
- Backend API endpoints (now database is ready)
- iOS/Android model layers
- Frontend state management setup

#### Phase 3: UI and Integration
Issues that depend on Phase 2:
- Frontend components and screens
- iOS/Android UI (now APIs are ready)
- Integration testing

#### Phase 4: Polish (Optional)
- Performance optimization
- Edge case handling
- Additional testing
- Documentation

### 5. Create Task Distribution Plan

```
# Task Distribution Plan

## Phase 1: Foundation [Days: X-Y]
Setup and base infrastructure

### Assigned to: @engineer_backend
- Issue BACK-01: [Title] - [Effort estimate]
  Prerequisites: None
  Blocked by: None
  Blocks: [Issue list]

### Assigned to: @engineer_backend
- Issue BACK-02: [Title] - [Effort estimate]
  Prerequisites: None
  Blocked by: None
  Blocks: [Issue list]

### Assigned to: Shared/All
- Issue SHARED-01: [Title] - [Effort estimate]
  Prerequisites: None
  Blocked by: None
  Blocks: [Issue list]

## Phase 2: APIs and Core [Days: Y-Z]
Implementation of primary features

### Assigned to: @engineer_frontend
- Issue FRONT-01: [Title] - [Effort estimate]
  Prerequisites: Issue SHARED-01 complete
  Blocked by: Issue BACK-01
  Blocks: Issue FRONT-02, FRONT-03

### Assigned to: @engineer_backend
- Issue BACK-03: [Title] - [Effort estimate]
  Prerequisites: None
  Blocked by: Issue BACK-01
  Blocks: Issue FRONT-01, MOBILE-01

### Assigned to: @engineer_ios
- Issue IOS-01: [Title] - [Effort estimate]
  Prerequisites: None
  Blocked by: Issue BACK-03
  Blocks: Issue IOS-02

### Assigned to: @engineer_android
- Issue ANDROID-01: [Title] - [Effort estimate]
  Prerequisites: None
  Blocked by: Issue BACK-03
  Blocks: Issue ANDROID-02

## Phase 3: Integration [Days: Z-A]
UI implementation and integration

### Assigned to: @engineer_frontend
- Issue FRONT-02: [Title] - [Effort estimate]
  Prerequisites: Issue FRONT-01 complete
  Blocked by: None
  Blocks: None

### Assigned to: @engineer_ios
- Issue IOS-02: [Title] - [Effort estimate]
  Prerequisites: Issue IOS-01 complete
  Blocked by: None
  Blocks: None

### Assigned to: @engineer_android
- Issue ANDROID-02: [Title] - [Effort estimate]
  Prerequisites: Issue ANDROID-01 complete
  Blocked by: None
  Blocks: None

## Parallel Work Opportunities
- Phase 1: All Phase 1 issues can run in parallel
- Phase 2: Frontend and Backend can run in parallel (they depend on Phase 1)
- Phase 2: iOS and Android can run in parallel (they depend on Backend)
- Phase 3: Frontend UI, iOS UI, and Android UI can run in parallel

## Critical Path
1. Issue SHARED-01 [X days]
2. Issue BACK-01 [Y days]
3. Issue BACK-03 [Z days]
4. Issue FRONT-01 [A days]
Total critical path: X+Y+Z+A days

## Execution Recommendations
1. Start Phase 1 immediately (all zero-dependency issues)
2. After Phase 1 done:
   - Start Backend API (BACK-03) and Frontend setup (FRONT-01) in parallel
   - Start iOS (IOS-01) and Android (ANDROID-01) in parallel (they wait on Backend)
3. After BACK-03 done, iOS/Android can proceed with UI
4. After FRONT-01 done, Frontend can proceed with UI
5. All Phase 3 work runs in parallel

## Team Allocation (if applicable)
- Backend: Issues BACK-01, BACK-02, BACK-03 (engineer_backend)
- Frontend: Issues FRONT-01, FRONT-02 (engineer_frontend)
- iOS: Issues IOS-01, IOS-02 (engineer_ios)
- Android: Issues ANDROID-01, ANDROID-02 (engineer_android)

## Potential Blockers
- Issue BACK-01 is critical path item
- Issue BACK-03 blocks iOS/Android work
- Delay in BACK-03 will delay mobile launch
```

### 6. Assign to Engineers
- Based on domain labels
- Consider engineer specialization
- Consider team capacity
- Track allocation for load balancing

### 7. Document Risk Mitigations
For critical path issues:
- Who is backup if primary engineer unavailable?
- What's the escalation path?
- What could cause delay?

## Output Expectations

### Task Distribution Plan
- Phase-based breakdown with effort estimates
- Clear dependency mapping
- Parallel work opportunities identified
- Critical path highlighted
- Team allocation documented

### Execution Board / Task List
```
STATUS    | ISSUE       | TITLE           | ASSIGNED TO      | DEPS    | BLOCKS  | EFFORT
----------|-------------|-----------------|------------------|---------|---------|-------
READY     | SHARED-01   | Setup DTOs      | All              | None    | BACK-01 | 2d
READY     | BACK-01     | DB Migration    | @engineer_backend| None    | BACK-03 | 1d
BLOCKED   | BACK-03     | User API        | @engineer_backend| BACK-01 | IOS-01  | 3d
BLOCKED   | FRONT-01    | Login Component | @engineer_frontend| SHARED-01,BACK-03 | FRONT-02 | 2d
BLOCKED   | IOS-01      | Auth Flow       | @engineer_ios    | BACK-03 | IOS-02  | 2d
BLOCKED   | ANDROID-01  | Auth Flow       | @engineer_android| BACK-03 | ANDROID-02 | 2d
BLOCKED   | FRONT-02    | User Dashboard  | @engineer_frontend| FRONT-01 | None  | 3d
BLOCKED   | IOS-02      | User Dashboard  | @engineer_ios    | IOS-01  | None    | 3d
BLOCKED   | ANDROID-02  | User Dashboard  | @engineer_android| ANDROID-01 | None | 3d
```

## Quality Checklist

- [ ] All issues assigned to appropriate engineer domain
- [ ] Dependencies clearly mapped
- [ ] No circular dependencies exist
- [ ] Critical path identified
- [ ] Parallel work opportunities highlighted
- [ ] Phase-based execution plan created
- [ ] Effort estimates provided
- [ ] Team allocation balanced
- [ ] Escalation procedures documented
- [ ] Risk mitigations for critical items identified

## Escalation Points

Stop and escalate when:
- Circular dependencies detected (issue A depends on B, B depends on A)
- Critical path is longer than acceptable timeline
- No parallel work opportunities exist (team can't be fully utilized)
- Resource/skills mismatch prevents assignment
- Issue depends on external work not yet started
