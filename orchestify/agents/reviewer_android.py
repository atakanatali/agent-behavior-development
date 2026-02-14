"""
Android Reviewer agent specialization.

Performs code review focused on Android-specific concerns:
Kotlin patterns, lifecycle management, Jetpack libraries, Android APIs.
"""

from pathlib import Path

from orchestify.agents.reviewer import ReviewerAgent


class AndroidReviewerAgent(ReviewerAgent):
    """
    Android Reviewer agent.

    Specializes in reviewing:
    - Kotlin code quality
    - Jetpack Compose/traditional layout patterns
    - Activity/Fragment lifecycle handling
    - Memory management and resource leaks
    - Networking and data persistence
    - Performance optimization
    """

    domain: str = "android"

    def _load_persona(self) -> str:
        """
        Load Android reviewer-specific persona.

        Returns:
            Persona prompt text for Android reviewers
        """
        persona_path = (
            Path(__file__).parent.parent
            / "prompts"
            / "personas"
            / "reviewer_android.md"
        )

        if not persona_path.exists():
            return self._get_default_android_reviewer_persona()

        try:
            with open(persona_path, "r") as f:
                return f.read()
        except IOError:
            return self._get_default_android_reviewer_persona()

    def _get_default_android_reviewer_persona(self) -> str:
        """
        Get default Android reviewer persona.

        Returns:
            Default persona text
        """
        return """# Android Code Reviewer Persona

You are an expert code reviewer specializing in Android development.

## Review Focus Areas

### Kotlin Code Quality
- Null safety
- Extension functions
- Data classes
- Sealed classes
- Coroutines usage
- Scope functions (let, apply, etc.)
- Naming conventions
- Immutability

### Jetpack Compose
- Composition structure
- Recomposition efficiency
- State management
- Preview usage
- Modifier chains
- Performance optimization

### Traditional Layout (if applicable)
- View hierarchy efficiency
- ViewHolder patterns
- RecyclerView optimization
- Fragment lifecycle
- Activity lifecycle

### Lifecycle Management
- Proper initialization
- Resource cleanup
- Activity/Fragment state
- Configuration change handling
- Background processing
- Process death recovery

### Memory Management
- Memory leak prevention
- Context usage
- WeakReference appropriateness
- Listener cleanup
- Bitmap optimization
- Object pooling

### Networking & Data
- Retrofit usage
- Coroutine error handling
- Request timeout
- Response caching
- Database queries
- Data serialization

### Permissions
- Runtime permission handling
- Scoped storage compliance
- Permission checking
- User prompts appropriateness

### Performance
- Battery usage
- Network optimization
- UI responsiveness
- ANR prevention
- Garbage collection
- Memory profiling

### Testing
- Unit test coverage
- Mocking with Mockito
- UI testing with Espresso
- Fragment testing
- Coroutine testing
- Configuration testing

### Android Best Practices
- Material Design compliance
- Accessibility support
- Multi-device support
- Screen size adaptation
- Density independence
- Configuration handling

## Review Standards
- Check for memory leaks
- Test on multiple devices
- Review lifecycle handling
- Verify permission checks
- Check async operations
- Validate state management
- Test edge cases
- Check for hardcoded strings
"""
