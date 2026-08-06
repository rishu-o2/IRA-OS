class RuntimeSubsystemError(Exception):
    """Base exception for the Runtime subsystem."""
    pass

class ValidationError(RuntimeSubsystemError):
    """Raised when an execution request or capability argument is invalid."""
    pass

class CapabilityNotFoundError(RuntimeSubsystemError):
    """Raised when a requested capability is not registered."""
    pass

class ExecutionFailedError(RuntimeSubsystemError):
    """Raised when an execution fails at the capability level."""
    pass
