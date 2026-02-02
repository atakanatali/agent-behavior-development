# Code Review Checklist (Full Stack)

Before submitting your code, verify:

## Architecture
- [ ] **Modules**: Is code in the correct layer? (Pres/App/Dom/Infra/Shared)
- [ ] **Registration**: Are services registered in `Shared.Registration`?
- [ ] **Communication**: Did you justify gRPC/REST/GraphQL?
- [ ] **ADR**: Is there an ADR for major architectural changes?

## Code Quality
- [ ] **SOLID**: Are classes Single Responsibility? Dependencies Injected? Liskov respected?
- [ ] **Complexity**: Method > 3 `if`s? -> Refactored to `Rule Pattern`?
- [ ] **Exceptions**: Is there global exception handling?
- [ ] **Logs**: Are logs structured and meaningful?
- [ ] **DRY**: Any duplicated logic? Extract to Shared.

## Dependencies
- [ ] **No Naked 3rd Party**: Are all external libs wrapped in a native interface?
- [ ] **Version Control**: Are packages managed in `Directory.Packages.props`?
- [ ] **Build**: properties managed in `Directory.Build.props`?

## Performance (Scale: 100M+)
- [ ] **Queries**: No N+1? Indexes present?
- [ ] **Async**: Everything awaited?
- [ ] **Efficiency**: Did you choose the most efficient structure?

## Documentation
- [ ] **Summary**: Did you provide a summary of changes?
