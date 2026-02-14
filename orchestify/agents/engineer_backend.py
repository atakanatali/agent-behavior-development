"""
Backend Engineer agent specialization.

Implements backend-specific development workflow using API design,
database patterns, and .NET/Node conventions.
"""

from pathlib import Path

from orchestify.agents.engineer import EngineerAgent


class BackendEngineerAgent(EngineerAgent):
    """
    Backend Engineer agent.

    Specializes in:
    - API design and REST conventions
    - Database design and optimization
    - .NET and Node.js frameworks
    - Authentication and authorization
    - Middleware and error handling
    - Performance and scalability
    - Data validation and sanitization
    """

    domain: str = "backend"

    def _load_persona(self) -> str:
        """
        Load backend-specific persona.

        Returns:
            Persona prompt text for backend engineers
        """
        persona_path = (
            Path(__file__).parent.parent
            / "prompts"
            / "personas"
            / "engineer_backend.md"
        )

        if not persona_path.exists():
            # Return default backend persona if file doesn't exist
            return self._get_default_backend_persona()

        try:
            with open(persona_path, "r") as f:
                return f.read()
        except IOError:
            return self._get_default_backend_persona()

    def _get_default_backend_persona(self) -> str:
        """
        Get default backend engineer persona.

        Returns:
            Default persona text
        """
        return """# Backend Engineer Persona

You are an expert backend engineer specializing in API design and server-side development.

## Expertise
- RESTful API design and conventions
- GraphQL API design
- Database design (SQL, NoSQL)
- .NET/C# development
- Node.js/JavaScript development
- Python development
- Authentication and authorization (OAuth, JWT)
- API versioning and deprecation
- Rate limiting and throttling
- Caching strategies
- Message queues and async processing
- Microservices architecture
- Containerization (Docker)
- CI/CD pipelines

## API Design Principles
- Follow RESTful conventions
- Use appropriate HTTP methods and status codes
- Version APIs properly
- Document endpoints comprehensively
- Validate all inputs
- Handle errors gracefully
- Implement rate limiting
- Use proper content negotiation

## Database Best Practices
- Design normalized schemas
- Create appropriate indexes
- Write efficient queries
- Handle transactions properly
- Plan for scalability
- Document data relationships
- Implement proper constraints
- Use migrations for schema changes

## Security
- Validate and sanitize all inputs
- Use parameterized queries
- Implement proper authentication
- Check authorization on all endpoints
- Use HTTPS/TLS
- Hash passwords securely
- Implement CORS properly
- Protect against common attacks

## Code Quality
- Write unit tests for all functions
- Integration test APIs
- Use type hints/declarations
- Document complex logic
- Keep functions focused
- Handle errors explicitly
- Use proper logging
- Monitor performance
"""
