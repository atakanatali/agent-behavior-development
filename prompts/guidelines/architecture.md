# Architecture Decision Reference

Architectural principles and default patterns for all ABD systems.

## Core Architecture: Modular Monolith

### Principle
Build as a single deployable unit initially, structured for future modularization.

### Why
- Simpler than microservices initially
- Easy to refactor into services later
- Clear service boundaries established through code layers
- Supports 100M+ users with proper design

### Service Boundaries
Each feature area is a module:
- Auth/Identity
- Users/Accounts
- Orders/Transactions
- Reporting/Analytics
- Notifications

### Internal vs. External APIs
- **Internal**: gRPC between modules (performance, type safety)
- **Public**: REST with OpenAPI documentation
- **Deprecation**: Versioning through URL paths or headers

## API Design Standards

### REST (Public APIs)

#### Principles
- **Resource-oriented**: Think in terms of resources, not RPC-style verbs
- **HTTP semantics**: Use GET, POST, PUT, DELETE, PATCH appropriately
- **Status codes**: Correct HTTP status for each response
- **Versioning**: Include version in URL path (/api/v1/) or header

#### Endpoint Patterns
```
GET    /api/users              # List users
GET    /api/users/:id          # Get user
POST   /api/users              # Create user
PUT    /api/users/:id          # Replace user
PATCH  /api/users/:id          # Partial update
DELETE /api/users/:id          # Delete user
```

#### Error Responses
```json
{
  "error": {
    "code": "INVALID_EMAIL",
    "message": "Email format invalid",
    "details": { "field": "email", "value": "notanemail" }
  }
}
```

#### Pagination
```
GET /api/users?page=1&limit=20&sort=createdAt:desc

Response includes:
- data: []
- pagination: { page: 1, limit: 20, total: 1000, pages: 50 }
```

### gRPC (Internal APIs)

#### Principles
- Type-safe
- High performance
- Strongly typed messages
- Bidirectional streaming support

#### When to Use gRPC
- Internal service-to-service communication
- Performance-critical interactions
- Real-time data streaming
- Microservice communication

#### Structure
```protobuf
service UserService {
  rpc GetUser (GetUserRequest) returns (UserResponse);
  rpc ListUsers (ListUsersRequest) returns (stream UserResponse);
}

message GetUserRequest {
  string user_id = 1;
}

message UserResponse {
  string id = 1;
  string email = 2;
  string name = 3;
  int64 created_at = 4;
}
```

### GraphQL (Optional, When Appropriate)

#### Use GraphQL When
- Complex, interconnected data
- Clients have varying data needs
- Avoiding over-fetching/under-fetching important
- Real-time subscriptions needed

#### Design Principles
- Type-safe schema
- Single endpoint
- Query optimization
- Subscriptions for real-time

#### Schema Structure
```graphql
type User {
  id: ID!
  email: String!
  name: String!
  orders: [Order!]!
  createdAt: DateTime!
}

type Query {
  user(id: ID!): User
  users(filter: UserFilter, limit: Int): [User!]!
}
```

## Data Architecture

### Database Design Principles
- **Normalize by default**: Reduce duplication
- **Denormalize strategically**: When performance justifies
- **Indexes strategically**: On foreign keys and filter columns
- **Query patterns first**: Design schema for read/write patterns

### Schema Strategy
```
Table: users
- id (PK)
- email (UNIQUE, INDEXED for login query)
- password_hash
- name
- created_at
- updated_at

Table: orders
- id (PK)
- user_id (FK, INDEXED)
- amount
- status (INDEXED for filtering)
- created_at

Index: orders(user_id, status) for "find pending orders by user"
```

### Scaling Strategies

#### Vertical Scaling (Initial)
- Larger database server
- Connection pooling
- Query optimization
- Caching layer

#### Horizontal Scaling (100M+ users)
- Database replication (read replicas)
- Sharding by user_id
- Separate read and write databases
- Cached read layer (Redis, Elasticsearch)

## State Management

### Backend State
- **Stateless by default**: Scale horizontally
- **Shared state**: Redis or database (not in-memory)
- **Session management**: Distributed (not in-process)
- **Cache invalidation**: TTL + event-driven

### Frontend State
- **Local state**: Component-level (@State in React)
- **Shared state**: Context or store (Zustand, Redux)
- **Server state**: API client cache (React Query, SWR)
- **Persistent state**: Local storage (user preferences)

### State Ownership
```
Component Local: Form inputs, UI toggles
Context/Store: User authentication, theme
Server: All persistent data
```

## Event-Driven Architecture

### When to Use Events
- Cross-module communication
- Async operations
- Audit trails
- Rebuilding cached data

### Event Patterns
```
Domain Event: UserCreated
- Trigger: User registration completes
- Published by: UserService
- Listeners: EmailService (send welcome), AnalyticsService (track signup)

Integration Event: OrderShipped
- Trigger: Order status changes to shipped
- Published by: OrderService
- Listeners: NotificationService (email customer), WarehouseService (update inventory)
```

### Event Structure
```json
{
  "eventId": "evt_123456",
  "eventType": "user.created",
  "timestamp": "2024-01-15T10:30:00Z",
  "version": 1,
  "aggregateId": "user_789",
  "data": {
    "userId": "user_789",
    "email": "user@example.com",
    "name": "John Doe"
  }
}
```

## CQRS Pattern (When Appropriate)

### Command Query Responsibility Segregation
Separate read and write models for complex domains.

### When to Use
- Read/write patterns are very different
- Reporting/querying is performance-critical
- Domain has complex aggregate roots
- Event sourcing is appropriate

### Pattern
```
Write Model (Commands):
- Normalize schema
- Enforce consistency
- Transactional

Read Model (Queries):
- Denormalized for performance
- Optimized for query patterns
- Updated through events
```

### Example: Order Domain
```
Write Commands:
- CreateOrder
- UpdateOrderStatus
- CancelOrder

Write Model:
- Normalization: Order → OrderItems
- Consistency: Inventory checks, pricing rules

Read Queries:
- GetActiveOrders (needs order + customer + items)
- GetOrderSummary (aggregated data)
- GetSalesByRegion (analytics)

Read Model:
- Denormalized view: order + customer + items + region data
- Updated asynchronously from events
```

## Security Architecture

### Defense in Depth
Multiple layers of security:

```
Layer 1: Infrastructure
- HTTPS only
- DDoS protection
- WAF (Web Application Firewall)

Layer 2: Application
- Input validation
- Output encoding
- Authentication/Authorization
- Rate limiting

Layer 3: Data
- Encryption at rest
- Encryption in transit
- Secrets management
- Audit logging
```

### Authentication Strategy
- **Session-based**: Server-side session store (stateful)
- **Token-based**: JWT tokens (stateless)
- **OAuth**: Third-party authentication
- **MFA**: Multi-factor authentication (optional)

### Authorization Strategy
- **Role-Based Access Control (RBAC)**: Users have roles, roles have permissions
- **Attribute-Based Access Control (ABAC)**: Fine-grained permissions based on attributes
- **Policy-based**: External policy engine

## Performance Optimization

### Caching Strategy
```
Layer 1: HTTP Caching
- Browser cache headers
- CDN caching
- API response caching

Layer 2: Application Caching
- Database query result caching
- Computed value caching
- Redis cache layer

Layer 3: Database
- Indexes
- Query optimization
- Connection pooling
```

### Database Performance
```
Query Optimization:
1. Index on filter columns (WHERE)
2. Index on sort columns (ORDER BY)
3. Batch load related data (N+1 prevention)
4. Query result limits

Common Patterns:
- SELECT * FROM users WHERE status = 'active' ORDER BY created_at DESC LIMIT 20
- CREATE INDEX idx_users_status_created ON users(status, created_at DESC)
```

### Asynchronous Operations
- Long-running operations in background
- Message queue for reliability
- Webhooks for cross-service events
- Polling fallback for stateless services

## Resilience & Reliability

### Fault Tolerance
- **Retry logic**: Exponential backoff for transient failures
- **Circuit breaker**: Fail fast if service down
- **Fallback**: Default behavior if dependency unavailable
- **Timeout**: Prevent infinite waiting

### Monitoring & Observability
```
Metrics:
- Request latency (p50, p95, p99)
- Error rates
- Throughput
- Resource usage (CPU, memory, disk)

Logging:
- Structured logs with context
- Request IDs for tracing
- Performance metrics
- Security events

Tracing:
- Distributed tracing
- Request flow across services
- Latency breakdown by component
```

### Deployment Strategy
- **Blue-green deployment**: Two identical environments, switch traffic
- **Canary deployment**: Gradual rollout to subset of users
- **Rolling deployment**: Gradual replacement of instances
- **Rollback plan**: Quick revert if issues detected

## Design for 100M+ Users

### Capacity Planning
- Estimate users, requests per second, data growth
- Plan for 10x growth without major redesign
- Monitor usage trends
- Proactive scaling

### Horizontal Scaling
- Stateless application servers
- Distributed caching
- Database replication and sharding
- Load balancing

### Performance Targets
- API latency: <200ms p95
- Page load: <3s
- Database query: <100ms p95
- 99.9% uptime (four nines)

## Technology Choices

### Backend Languages
- **Node.js**: Rapid development, great for I/O-heavy apps
- **.NET**: Strong typing, good performance, enterprise-friendly
- **Python**: Great for rapid prototyping, good for ML/data

### Frontend Framework
- **React**: Flexible, large ecosystem, component-driven
- **Vue**: Simpler learning curve, progressive enhancement
- **Angular**: Full framework, good for enterprise

### Mobile
- **Native**: iOS (Swift), Android (Kotlin) for best performance
- **Cross-platform**: React Native, Flutter for code sharing

### Database
- **Relational (PostgreSQL)**: Structured data, transactions
- **Document (MongoDB)**: Flexible schema, scalability
- **Cache (Redis)**: Fast access, sessions, queues

### Message Queue
- **RabbitMQ**: Reliability, complex routing
- **Apache Kafka**: High throughput, event streaming
- **AWS SQS**: Managed, cloud-native

## Architectural Evolution

### Starting Point
Simple monolith with clear layers, REST API.

### Growing to 10M Users
- Add caching layer (Redis)
- Read replicas for database
- Separate logging/monitoring
- Content delivery network (CDN)

### Scaling to 100M+ Users
- Event-driven architecture
- CQRS for complex domains
- Microservices for independent scaling
- Multiple databases for different data types
- Advanced caching strategies

## Principles Summary

1. **Start simple**: Monolith with clear layers
2. **Design for scale**: Plan for 100M+ from day one
3. **Separate concerns**: Clear boundaries between layers
4. **Stateless services**: Enable horizontal scaling
5. **Async operations**: Don't block on I/O
6. **Cache strategically**: Eliminate unnecessary work
7. **Monitor everything**: Observability from the start
8. **Plan for failure**: Resilience built in
9. **Iterate on design**: Refactor as requirements evolve
10. **Document decisions**: Architecture decision records

---

These architectural principles form the foundation for building scalable, maintainable systems that can grow from MVP to 100M+ users.
