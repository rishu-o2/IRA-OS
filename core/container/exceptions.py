class ContainerError(Exception):
    """Base exception for all Dependency Injection Container errors."""
    pass

class RegistrationError(ContainerError):
    """Raised when there is an issue with registering a component."""
    pass

class ResolutionError(ContainerError):
    """Raised when a dependency cannot be resolved."""
    pass

class CircularDependencyError(ResolutionError):
    """Raised when a circular dependency is detected."""
    pass

class ValidationError(ContainerError):
    """Raised when the container graph validation fails."""
    pass
