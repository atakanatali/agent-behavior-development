# ABD Orchestration Engine - Prompt Artifacts

Complete set of versioned, structured prompt artifacts for the Agent Behavior Development (ABD) orchestration engine. These artifacts define roles, goals, guardrails, workflows, and standards for autonomous agent orchestration in software development.

## Overview

This directory contains 30 comprehensive prompt files organized into 5 categories:
- **11 Personas**: Agent roles with identity, goals, and behavioral guidelines
- **8 Workflows**: Step-by-step procedures for major phases of development
- **5 Templates**: Standardized formats for issues, PRs, reviews, and assessments
- **4 Guardrails**: Universal rules that all agents must follow
- **2 Guidelines**: Reference architectures and project structures

**Total**: 7,896 lines of comprehensive prompt documentation.

---

## Directory Structure

```
prompts/
├── personas/              # Agent role definitions (11 files)
├── workflows/             # Development phase procedures (8 files)
├── templates/             # Standardized output formats (5 files)
├── guardrails/            # Universal rules (4 files)
├── guidelines/            # Reference architectures (2 files)
└── README.md             # This file
```

---

## PERSONAS (11 Agent Roles)

Each persona defines how an agent should think, behave, and make decisions within their domain.

### Product & Project Management
- **`personas/tpm.md`** - Technical Product Manager (109 lines)
  - Translates user intent into comprehensive specifications
  - Creates detailed issues with high-order thinking
  - Groups issues into logical epics
  - Asks clarifying questions; max ~20 changes per issue

### Architecture & Leadership
- **`personas/architect.md`** - Team Lead Architect (125 lines)
  - Reviews issues for architectural fit
  - Makes SOLID/DRY/Clean Architecture decisions
  - Designs for 100M+ scale
  - Final arbiter of system design before merge

### Engineering - Frontend
- **`personas/engineer_frontend.md`** - Senior Frontend Engineer (138 lines)
  - React/Next.js/TypeScript expert
  - Component-driven architecture
  - Responsive design, accessibility, performance
  - State management expertise

### Engineering - Backend
- **`personas/engineer_backend.md`** - Senior Backend Engineer (163 lines)
  - .NET/Node.js/Python expert
  - API design (REST, gRPC, GraphQL)
  - Database optimization, CQRS, event sourcing
  - Microservice/modular monolith architecture

### Engineering - iOS
- **`personas/engineer_ios.md`** - Senior iOS Engineer (166 lines)
  - Swift/SwiftUI expert
  - iOS HIG compliance
  - Core Data, Combine, async/await
  - App Store guidelines, memory optimization

### Engineering - Android
- **`personas/engineer_android.md`** - Senior Android Engineer (170 lines)
  - Kotlin/Jetpack Compose expert
  - Material Design 3 compliance
  - Room, Coroutines, Flow
  - Play Store guidelines, battery optimization

### Code Review - Frontend
- **`personas/reviewer_frontend.md`** - Senior Frontend Code Reviewer (144 lines)
  - Reviews component quality, accessibility, performance
  - Checks React patterns, hook usage, security (XSS, injection)
  - Validates responsive design and browser compatibility

### Code Review - Backend
- **`personas/reviewer_backend.md`** - Senior Backend Code Reviewer (152 lines)
  - Reviews API design quality, database optimization
  - Checks SOLID compliance, error handling, security
  - Performance review (N+1 queries, indexing, async)

### Code Review - iOS
- **`personas/reviewer_ios.md`** - Senior iOS Code Reviewer (168 lines)
  - Reviews Swift patterns, memory management
  - Checks HIG compliance, accessibility
  - Validates lifecycle management, threading

### Code Review - Android
- **`personas/reviewer_android.md`** - Senior Android Code Reviewer (169 lines)
  - Reviews Kotlin patterns, memory management
  - Checks Material Design compliance, accessibility
  - Validates lifecycle, coroutine usage

### Quality Assurance
- **`personas/qa.md`** - QA Tester (152 lines)
  - Validates implementation against specification
  - Security testing (OWASP, injection, XSS, CSRF)
  - Edge case and regression risk assessment

---

## WORKFLOWS (8 Development Phases)

Each workflow is a step-by-step guide for major phases in the development process.

1. **`workflows/spec_gathering.md`** (163 lines)
   - Convert user requests into comprehensive specifications
   - Identify ambiguities and ask clarifying questions
   - Produce detailed acceptance criteria and technical context

2. **`workflows/issue_creation.md`** (215 lines)
   - Break specifications into discrete, implementable issues
   - Max ~15-20 changes per issue
   - Group issues into epics with proper sequencing

3. **`workflows/technical_design.md`** (205 lines)
   - Review issues for architectural compliance
   - Assign domain labels (frontend/backend/ios/android)
   - Add technical details and architecture decisions

4. **`workflows/task_distribution.md`** (269 lines)
   - Map issues to engineer roles by domain
   - Define execution order and identify dependencies
   - Optimize parallel work opportunities

5. **`workflows/code_generation.md`** (339 lines)
   - Convert issue specifications into high-quality code
   - Include testing, documentation, and self-fix context
   - Provide code in structured change format

6. **`workflows/code_review.md`** (285 lines)
   - Review code against standards and domain-specific criteria
   - Check SOLID principles, security, performance
   - Provide constructive feedback with clear severity levels

7. **`workflows/qa_testing.md`** (405 lines)
   - Validate implementation against specification
   - Test functional, security, performance, regression scenarios
   - Document findings with clear reproduction steps

8. **`workflows/final_review.md`** (350 lines)
   - Architect final validation before merge
   - Ensure architectural compliance and project structure integrity
   - Verify performance, security, and testing adequacy

---

## TEMPLATES (5 Standardized Formats)

Proven templates for key artifacts in the ABD system.

1. **`templates/issue_template.md`** (294 lines)
   - Complete ABD issue format with all required sections
   - Includes: Goal, Context, Acceptance Criteria, Behavior Spec, Technical Approach, Done Checklist, Risks
   - Example: User authentication issue with detailed specifications

2. **`templates/pr_template.md`** (332 lines)
   - Pull Request description template
   - Includes: What Changed, Implementation Details, Testing, Security, Performance, Dependencies
   - Quality checklist for reviewers

3. **`templates/review_comment.md`** (405 lines)
   - Constructive code review comment formats
   - Blocking issues, major issues, suggestions, questions
   - Examples across security, performance, and code quality domains

4. **`templates/scorecard.md`** (405 lines)
   - Dimensional quality assessment template
   - 5 dimensions: Functionality, Code Quality, Testing, Performance, Security
   - Pass/Conditional/Fail decision framework

5. **`templates/recycle_output.md`** (395 lines)
   - Handoff summary at major transitions
   - Tracks: Kept (ready to use), Reused (with modifications), Banned (rejected)
   - Knowledge transfer and risk documentation

---

## GUARDRAILS (4 Universal Rules)

Mandatory standards that apply to all agents across all domains.

1. **`guardrails/global_rules.md`** (229 lines)
   - Communication and output format requirements
   - Honesty about facts vs. assumptions
   - Quality standards (SOLID, DRY, testing)
   - Escalation protocols

2. **`guardrails/code_standards.md`** (391 lines)
   - SOLID principles (mandatory for all)
   - DRY, KISS, YAGNI principles
   - Naming conventions by language
   - Performance standards (N+1 queries, async/await, caching)
   - Testing requirements (>80% coverage)
   - Memory management and null safety

3. **`guardrails/security_rules.md`** (354 lines)
   - Authentication & authorization requirements
   - Input validation (mandatory at boundaries)
   - SQL injection prevention
   - XSS prevention
   - Secrets management (no hardcoding)
   - OWASP Top 10 coverage
   - Encryption (at rest and in transit)

4. **`guardrails/issue_guidelines.md`** (381 lines)
   - Completeness requirements for all issues
   - Language and clarity standards
   - Acceptance criteria format
   - Behavior specification requirements
   - Technical approach specification
   - Done checklist requirements
   - Risk identification standards
   - Quality gate before implementation

---

## GUIDELINES (2 Reference Documents)

Architectural and structural references for system design.

1. **`guidelines/project_structure.md`** (359 lines)
   - Complete project organization for full-stack applications
   - Frontend (React/Next.js): components, hooks, services, state management
   - Backend (Modular Monolith): presentation, application, domain, infrastructure layers
   - iOS (Swift/SwiftUI): features, view models, services
   - Android (Kotlin/Compose): features, view models, repositories
   - Shared code structure
   - Documentation organization
   - Testing hierarchy

2. **`guidelines/architecture.md`** (464 lines)
   - Core architecture: Modular Monolith with service boundaries
   - API design standards: REST (public), gRPC (internal), GraphQL (optional)
   - Data architecture: normalization, indexing, scaling strategies
   - State management patterns
   - Event-driven architecture
   - CQRS pattern (when appropriate)
   - Security architecture (defense in depth)
   - Performance optimization strategies
   - Resilience & reliability patterns
   - Design for 100M+ users

---

## Usage Guide

### For Agents
Each agent should reference their relevant files:
- **TPM**: Read `personas/tpm.md`, then use `workflows/spec_gathering.md` → `workflows/issue_creation.md`
- **Architect**: Read `personas/architect.md`, then use `workflows/technical_design.md` → `workflows/final_review.md`
- **Frontend Engineer**: Read `personas/engineer_frontend.md`, then use `workflows/code_generation.md`
- **Backend Engineer**: Read `personas/engineer_backend.md`, then use `workflows/code_generation.md`
- **iOS Engineer**: Read `personas/engineer_ios.md`, then use `workflows/code_generation.md`
- **Android Engineer**: Read `personas/engineer_android.md`, then use `workflows/code_generation.md`
- **Frontend Reviewer**: Read `personas/reviewer_frontend.md`, then use `workflows/code_review.md` with `templates/review_comment.md`
- **Backend Reviewer**: Read `personas/reviewer_backend.md`, then use `workflows/code_review.md` with `templates/review_comment.md`
- **iOS Reviewer**: Read `personas/reviewer_ios.md`, then use `workflows/code_review.md` with `templates/review_comment.md`
- **Android Reviewer**: Read `personas/reviewer_android.md`, then use `workflows/code_review.md` with `templates/review_comment.md`
- **QA**: Read `personas/qa.md`, then use `workflows/qa_testing.md`

### For Project Setup
1. Read `guidelines/project_structure.md` to set up project organization
2. Read `guidelines/architecture.md` to understand system design decisions
3. Apply `guardrails/` standards to all code

### For Issue Management
1. Use `workflows/spec_gathering.md` to gather requirements
2. Use `templates/issue_template.md` to create issues
3. Validate against `guardrails/issue_guidelines.md`
4. Use `workflows/issue_creation.md` to break into implementable pieces

### For Code Quality
1. Reference `guardrails/code_standards.md` for quality requirements
2. Reference `guardrails/security_rules.md` for security requirements
3. Use domain-specific reviewer persona for code review
4. Use `templates/review_comment.md` for feedback format

---

## Key Principles

1. **All code must follow guardrails**: No exceptions, applied universally
2. **Personas define agent behavior**: Each role has clear identity and goals
3. **Workflows are step-by-step guides**: For major development phases
4. **Templates ensure consistency**: Across issues, PRs, reviews, assessments
5. **Quality gates prevent rework**: Issues quality-checked before implementation
6. **Security is non-negotiable**: OWASP coverage mandatory
7. **Design for 100M+ users**: Scalability built in from day one
8. **Clear handoffs between agents**: Using Recycle Output template

---

## File Statistics

- **Total files**: 30 comprehensive prompt artifacts
- **Total lines**: 7,896 lines of documentation
- **Coverage**: Personas (1,836 lines), Workflows (2,231 lines), Templates (1,831 lines), Guardrails (1,355 lines), Guidelines (823 lines)

---

## Version Control

All prompt changes must be versioned:
- Include timestamp of change
- Document what changed and why
- Reference issue or decision that prompted change
- Maintain backwards compatibility when possible

---

## Maintenance

### Quarterly Review
- Check if persona behaviors match team needs
- Validate workflows are being followed
- Review guardrails for new security/quality issues
- Update templates based on lessons learned

### When Updating
- Update one file at a time
- Test with actual agents
- Document rationale for changes
- Communicate changes to team

---

## Quick Reference

### All Agents Must Know
- `guardrails/global_rules.md`: Communication, quality, escalation
- `guardrails/code_standards.md`: SOLID, DRY, KISS, YAGNI
- `guardrails/security_rules.md`: Authentication, input validation, secrets
- `guidelines/architecture.md`: System design principles

### By Agent Role
- See corresponding persona file for identity and behavioral guidelines
- See corresponding workflow file for step-by-step procedures
- See corresponding template file for output format

---

## Support

For questions about:
- **Agent behavior**: Read persona file
- **How to execute task**: Read workflow file
- **Output format**: Read template file
- **Code quality**: Read guardrails files
- **System architecture**: Read guidelines files

---

This comprehensive prompt system enables autonomous agent orchestration with:
- Clear roles and responsibilities
- Step-by-step workflows for all major phases
- Quality gates preventing rework
- Consistent communication formats
- Universal security and quality standards
- Architecture designed for scale

Generated: 2024-01-15
Last Updated: 2024-01-15
Version: 1.0.0
