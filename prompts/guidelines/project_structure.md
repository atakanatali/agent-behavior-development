# Project Structure Reference

Standard project organization for full-stack applications with frontend, backend, and mobile platforms.

## Root Level

```
project-root/
├── frontend/              # Web application (React/Next.js)
├── backend/               # API server (Node.js/.NET/Python)
├── ios/                   # iOS application (Swift/SwiftUI)
├── android/               # Android application (Kotlin/Compose)
├── shared/                # Shared code, types, contracts
├── docs/                  # Documentation
├── .gitignore
├── README.md
└── package.json or equivalent
```

## Frontend Structure (React/Next.js)

```
frontend/
├── public/                # Static assets
│   ├── images/
│   ├── icons/
│   └── favicon.ico
├── src/
│   ├── components/
│   │   ├── common/        # Reusable components (Button, Modal, etc.)
│   │   ├── layout/        # Layout components (Header, Sidebar, etc.)
│   │   ├── pages/         # Page-level components
│   │   └── features/      # Feature-specific components
│   │       ├── auth/
│   │       ├── users/
│   │       └── [feature]/
│   ├── hooks/             # Custom React hooks
│   ├── context/           # React Context for global state
│   ├── store/             # State management (Zustand, Redux, etc.)
│   ├── services/          # API clients, utilities
│   │   ├── api.ts         # API client configuration
│   │   ├── authService.ts
│   │   └── [domain]Service.ts
│   ├── styles/            # Global styles
│   │   ├── globals.css
│   │   └── variables.css
│   ├── types/             # TypeScript types (duplicate of shared if needed)
│   ├── utils/             # Utility functions
│   ├── App.tsx            # Root component
│   └── main.tsx           # Entry point
├── tests/                 # Test files
├── package.json
├── tsconfig.json
└── .env.example           # Environment variables template
```

### Component Organization
Each feature should follow this pattern:
```
components/features/auth/
├── LoginForm.tsx          # Main component
├── LoginForm.test.tsx     # Component tests
├── LoginForm.module.css   # Component styles (if not using CSS-in-JS)
├── types.ts               # Component-specific types
└── useLoginForm.ts        # Component-specific hooks
```

## Backend Structure (Modular Monolith)

```
backend/
├── src/
│   ├── presentation/      # HTTP/gRPC handlers, controllers
│   │   ├── middleware/    # Express/Koa middleware
│   │   ├── routes/        # Route definitions
│   │   ├── controllers/   # Request handlers
│   │   └── validation/    # Request validation
│   ├── application/       # Application/orchestration layer
│   │   ├── services/      # Application services (business rules)
│   │   ├── mappers/       # DTO mappers
│   │   └── events/        # Event handlers
│   ├── domain/            # Domain/business logic layer
│   │   ├── entities/      # Domain entities
│   │   ├── value-objects/ # Value objects
│   │   ├── repositories/  # Repository interfaces (not implementations)
│   │   ├── services/      # Domain services
│   │   └── events/        # Domain events
│   ├── infrastructure/    # Infrastructure/external concerns
│   │   ├── database/      # Database connection, migrations
│   │   ├── persistence/   # Repository implementations
│   │   ├── external-api/  # Third-party service calls
│   │   ├── cache/         # Caching layer
│   │   └── messaging/     # Message queue integration
│   ├── shared/            # Cross-cutting concerns
│   │   ├── exceptions/    # Custom exceptions
│   │   ├── logging/       # Logging setup
│   │   ├── security/      # Security utilities
│   │   ├── utils/         # Helper functions
│   │   └── constants/     # Global constants
│   ├── config/            # Configuration
│   │   ├── database.ts
│   │   ├── cache.ts
│   │   └── env.ts
│   ├── types/             # Type definitions
│   └── index.ts           # Application entry point
├── tests/
│   ├── unit/              # Unit tests
│   ├── integration/       # Integration tests
│   └── fixtures/          # Test data and mocks
├── migrations/            # Database migrations
├── seeds/                 # Database seeds
├── docs/                  # API documentation
├── .env.example
├── package.json
└── tsconfig.json
```

### Layering Architecture
```
Presentation Layer (HTTP/gRPC)
    ↓ (request)
Application Layer (Services, Use Cases)
    ↓ (domain model)
Domain Layer (Business Logic, Entities)
    ↓ (repository interface)
Infrastructure Layer (Database, External APIs)
```

## iOS Structure (Swift/SwiftUI)

```
ios/
├── App/                   # Main app structure
│   ├── [AppName]App.swift # App entry point
│   └── AppDelegate.swift  # App lifecycle
├── Features/              # Feature modules (MVVM)
│   ├── Auth/
│   │   ├── Views/         # SwiftUI views
│   │   ├── ViewModels/    # MVVM ViewModels
│   │   ├── Models/        # Data models
│   │   └── Services/      # Domain services
│   ├── Users/
│   │   ├── Views/
│   │   ├── ViewModels/
│   │   ├── Models/
│   │   └── Services/
│   └── [Feature]/
├── Shared/                # Shared code
│   ├── Models/            # Shared data models
│   ├── Services/          # Shared services (API, storage)
│   ├── Utilities/         # Utility functions
│   ├── Extensions/        # Swift extensions
│   ├── Components/        # Reusable SwiftUI components
│   └── Theme/             # Design tokens, colors
├── Network/               # API client
│   ├── APIClient.swift
│   ├── Endpoints.swift
│   └── Models/            # API response models
├── Storage/               # Data persistence
│   ├── LocalStorage.swift
│   └── CoreDataStack.swift
├── Resources/
│   ├── Localizable.strings # Localization
│   ├── Assets/            # Images, icons, colors
│   └── Fonts/
└── Tests/
    ├── Unit/
    └── Integration/
```

## Android Structure (Kotlin/Compose)

```
android/
├── app/
│   ├── src/
│   │   ├── main/
│   │   │   ├── kotlin/
│   │   │   │   ├── MainActivity.kt
│   │   │   │   ├── features/           # Feature modules (MVVM)
│   │   │   │   │   ├── auth/
│   │   │   │   │   │   ├── screens/    # Composable screens
│   │   │   │   │   │   ├── viewmodels/ # MVVM ViewModels
│   │   │   │   │   │   ├── models/     # Data models
│   │   │   │   │   │   └── repositories/ # Data repositories
│   │   │   │   │   ├── users/
│   │   │   │   │   └── [feature]/
│   │   │   │   ├── shared/
│   │   │   │   │   ├── models/         # Shared data models
│   │   │   │   │   ├── services/       # Shared services
│   │   │   │   │   ├── utils/          # Utility functions
│   │   │   │   │   ├── components/     # Reusable Composables
│   │   │   │   │   └── theme/          # Material Design theme
│   │   │   │   ├── network/            # API client (Retrofit)
│   │   │   │   │   ├── ApiService.kt
│   │   │   │   │   └── models/         # API models
│   │   │   │   └── data/
│   │   │   │       ├── database/       # Room database
│   │   │   │       └── preferences/    # DataStore
│   │   │   ├── res/
│   │   │   │   ├── drawable/
│   │   │   │   ├── values/
│   │   │   │   └── [language]/
│   │   │   └── AndroidManifest.xml
│   │   └── test/
│   │       └── java/                   # Unit tests
│   └── build.gradle
└── gradle/
```

## Shared Structure

```
shared/
├── types/                 # Shared type definitions
│   ├── User.ts            # User entity
│   ├── Auth.ts            # Authentication types
│   └── [domain].ts        # Domain types
├── models/                # Shared data models
│   ├── DTOs/              # Data Transfer Objects
│   ├── responses/         # API response models
│   └── requests/          # API request models
├── contracts/             # API/Service contracts
│   ├── UserService.ts     # Service interfaces
│   └── [domain].ts        # Domain service interfaces
├── validation/            # Shared validation schemas
│   ├── userSchema.ts
│   └── [domain]Schema.ts
├── enums/                 # Shared enumerations
├── constants/             # Shared constants
└── utils/                 # Shared utilities
    ├── formatting.ts
    ├── parsing.ts
    └── helpers.ts
```

## Documentation Structure

```
docs/
├── README.md              # Project overview
├── SETUP.md               # Development setup guide
├── ARCHITECTURE.md        # Architecture decisions
├── API.md                 # API documentation
├── DATABASE.md            # Database schema and migrations
├── DEPLOYMENT.md          # Deployment procedures
├── SECURITY.md            # Security practices
├── CONTRIBUTING.md        # Contribution guidelines
├── guides/
│   ├── local-development.md
│   ├── testing.md
│   └── debugging.md
└── api/
    ├── auth.md            # Auth endpoints
    ├── users.md           # User endpoints
    └── [domain].md        # Domain endpoints
```

## Testing Structure

All projects follow this testing hierarchy:

```
tests/
├── unit/                  # Unit tests (business logic)
│   ├── services/
│   ├── utils/
│   └── models/
├── integration/           # Integration tests (workflows)
│   ├── api/
│   ├── database/
│   └── features/
├── e2e/                   # End-to-end tests (full flows)
├── fixtures/              # Test data
└── mocks/                 # Mock implementations
```

## Configuration Files

### Frontend
```
frontend/
├── .env.example           # Env vars template
├── .eslintrc.json         # Linting rules
├── .prettierrc             # Code formatting
├── tsconfig.json          # TypeScript config
├── vite.config.ts or      # Build config
│  webpack.config.js
└── package.json
```

### Backend
```
backend/
├── .env.example           # Env vars template
├── .eslintrc.json         # Linting rules
├── tsconfig.json          # TypeScript config (if Node.js)
├── .prettierrc             # Code formatting
├── docker-compose.yml     # Development environment
├── Dockerfile             # Production container
└── package.json or
   requirements.txt or
   pom.xml
```

### Mobile
```
ios/
├── .gitignore
├── Podfile                # Dependency management
└── Xcodeproj/             # Xcode project

android/
├── .gitignore
├── build.gradle
├── local.properties       # Local SDK paths
└── gradle.properties
```

## Key Principles

### 1. Separation of Concerns
- Each layer has specific responsibility
- No business logic in presentation
- No presentation logic in domain
- No infrastructure concerns in business logic

### 2. DRY (Don't Repeat Yourself)
- Share common code via shared/
- Duplicate code only when domain-specific
- Extract reusable components

### 3. Scalability
- Structure supports 100M+ users
- Easy to split into microservices later
- Clear service boundaries

### 4. Testability
- Services injectable
- Dependencies explicit
- Easy to mock external services

### 5. Maintainability
- Consistent structure across platforms
- Easy to onboard new developers
- Clear where code lives

## Migration from Non-Standard Structure

If migrating from different structure:
1. Keep existing structure initially
2. New code follows this structure
3. Refactor gradually when touching existing code
4. Set timeline for full migration
5. Document interim structure in README

---

All new projects should follow this structure. Existing projects should migrate to this structure following the migration guidelines above.
