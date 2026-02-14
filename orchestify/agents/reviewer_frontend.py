"""
Frontend Reviewer agent specialization.

Performs code review focused on frontend-specific concerns:
React/Next.js patterns, CSS, component architecture, accessibility.
"""

from pathlib import Path

from orchestify.agents.reviewer import ReviewerAgent


class FrontendReviewerAgent(ReviewerAgent):
    """
    Frontend Reviewer agent.

    Specializes in reviewing:
    - React/Next.js code
    - Component design and reusability
    - CSS and styling approaches
    - Accessibility standards
    - Performance optimization
    - Testing practices
    """

    domain: str = "frontend"

    def _load_persona(self) -> str:
        """
        Load frontend reviewer-specific persona.

        Returns:
            Persona prompt text for frontend reviewers
        """
        persona_path = (
            Path(__file__).parent.parent
            / "prompts"
            / "personas"
            / "reviewer_frontend.md"
        )

        if not persona_path.exists():
            return self._get_default_frontend_reviewer_persona()

        try:
            with open(persona_path, "r") as f:
                return f.read()
        except IOError:
            return self._get_default_frontend_reviewer_persona()

    def _get_default_frontend_reviewer_persona(self) -> str:
        """
        Get default frontend reviewer persona.

        Returns:
            Default persona text
        """
        return """# Frontend Code Reviewer Persona

You are an expert code reviewer specializing in frontend development.

## Review Focus Areas

### Component Design
- Single responsibility principle
- Proper prop interfaces
- Composition over inheritance
- Render performance
- Memoization where appropriate
- Hook usage patterns

### Accessibility (a11y)
- Semantic HTML usage
- ARIA attributes
- Keyboard navigation
- Color contrast
- Focus management
- Alt text for images
- Screen reader testing

### Performance
- Bundle size impact
- Unnecessary re-renders
- Image optimization
- Code splitting
- Lazy loading
- Cache utilization

### CSS and Styling
- CSS specificity
- Responsive design
- Mobile-first approach
- CSS-in-JS best practices
- Theme consistency
- Animation performance

### Testing
- Test coverage
- Component isolation
- User interaction testing
- Edge case coverage
- Accessibility testing
- Visual regression testing

### Code Quality
- TypeScript usage
- Error boundaries
- Error handling
- Null safety
- Documentation
- Code clarity

## Review Standards
- Check for console errors/warnings
- Verify responsive design
- Test keyboard navigation
- Review prop drilling
- Check for memory leaks
- Validate styling consistency
- Ensure tests are meaningful
- Check for hardcoded values
"""
