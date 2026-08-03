class LifecycleError(Exception):
    """Base exception for all Lifecycle Manager errors."""
    pass


class StartupError(LifecycleError):
    """Raised when a component fails to start."""
    pass


class ShutdownError(LifecycleError):
    """Raised when a component fails to stop or shut down."""
    pass


class RegistrationError(LifecycleError):
    """Raised when there is an issue registering a component."""
    pass


class HealthCheckError(LifecycleError):
    """Raised when a component fails its health check."""
    pass
