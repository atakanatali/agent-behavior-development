"""
Frontend Engineer agent specialization.

Implements frontend-specific development workflow using React/Next.js,
CSS, and component architecture patterns.
"""

from pathlib import Path

from orchestify.agents.engineer import EngineerAgent


class FrontendEngineerAgent(EngineerAgent):
    """
    Frontend Engineer agent.

    Specializes in:
    - React/Next.js development
    - Component architecture
    - CSS and styling
    - UI/UX implementation
    - Frontend testing
    """

    domain: str = "frontend"

    def _load_persona(self) -> str:
        """
        Load frontend-specific persona.

        Returns:
            Persona prompt text for frontend engineers
        """
        persona_path = (
            Path(__file__).parent.parent
            / "prompts"
            / "personas"
            / "engineer_frontend.md"
        )

        if not persona_path.exists():
            # Return default frontend persona if file doesn't exist
            return self._get_default_frontend_persona()

        try:
            with open(persona_path, "r") as f:
                return f.read()
        except IOError:
            return self._get_default_frontend_persona()

    def _get_default_frontend_persona(self) -> str:
        """
        Get default frontend engineer persona.

        Returns:
            Default persona text
        """
        return """# Frontend Engineer Persona

You are an expert frontend engineer specializing in React/Next.js development.

## Expertise
- React and Next.js frameworks
- TypeScript for type safety
- Modern CSS (Tailwind, CSS Modules, Styled Components)
- Component-based architecture
- UI/UX best practices
- Performance optimization
- Accessibility (a11y) standards
- Web standards and browser compatibility
- Testing (Jest, React Testing Library, Playwright)

## Guidelines
- Write semantic, accessible HTML
- Use component composition for reusability
- Follow established component patterns
- Optimize for performance and bundle size
- Write comprehensive tests
- Document component APIs
- Follow project styling conventions
- Ensure responsive design
- Handle edge cases gracefully
- Use proper error boundaries

## Code Quality
- Lint code with ESLint
- Format with Prettier
- Run tests before committing
- Document complex logic
- Keep components focused
- Use proper TypeScript types
"""
