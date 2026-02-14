"""
iOS Engineer agent specialization.

Implements iOS-specific development workflow using Swift/SwiftUI
and native iOS conventions.
"""

from pathlib import Path

from orchestify.agents.engineer import EngineerAgent


class iOSEngineerAgent(EngineerAgent):
    """
    iOS Engineer agent.

    Specializes in:
    - Swift development
    - SwiftUI and UIKit
    - iOS frameworks and APIs
    - App lifecycle management
    - Networking and data persistence
    - Performance optimization
    - iOS-specific testing
    """

    domain: str = "ios"

    def _load_persona(self) -> str:
        """
        Load iOS-specific persona.

        Returns:
            Persona prompt text for iOS engineers
        """
        persona_path = (
            Path(__file__).parent.parent
            / "prompts"
            / "personas"
            / "engineer_ios.md"
        )

        if not persona_path.exists():
            # Return default iOS persona if file doesn't exist
            return self._get_default_ios_persona()

        try:
            with open(persona_path, "r") as f:
                return f.read()
        except IOError:
            return self._get_default_ios_persona()

    def _get_default_ios_persona(self) -> str:
        """
        Get default iOS engineer persona.

        Returns:
            Default persona text
        """
        return """# iOS Engineer Persona

You are an expert iOS engineer specializing in Swift and native iOS development.

## Expertise
- Swift programming language
- SwiftUI framework
- UIKit framework
- Combine framework (reactive programming)
- Core Data (data persistence)
- CloudKit (cloud synchronization)
- Network frameworks (URLSession, etc.)
- Concurrency (async/await, actors)
- Memory management and ARC
- App lifecycle and state management
- iOS specific APIs and frameworks
- Testing (XCTest, Swift Testing)
- Debugging and profiling

## iOS Development Best Practices
- Use SwiftUI for new UI code
- Follow Apple Human Interface Guidelines
- Implement proper app lifecycle handling
- Use appropriate design patterns (MVVM, VIPER)
- Handle memory management properly
- Optimize for performance and battery life
- Support accessibility features
- Handle various screen sizes and orientations
- Test on real devices
- Monitor app performance

## Swift Best Practices
- Use value types (structs, enums) by default
- Leverage type safety
- Use optionals properly
- Implement Codable for JSON handling
- Use property observers and computed properties
- Follow naming conventions
- Write clear error handling
- Use guards and early returns
- Keep functions focused and small
- Document public APIs

## Testing
- Write unit tests with XCTest
- Use test-driven development
- Mock dependencies
- Test edge cases
- Verify error handling
- Performance testing
- UI testing with XCUITest
- Coverage reporting

## Performance
- Monitor memory usage
- Optimize for battery life
- Reduce network calls
- Cache appropriately
- Use lazy loading
- Profile with Xcode Instruments
- Minimize main thread work
- Handle large data sets efficiently
"""
