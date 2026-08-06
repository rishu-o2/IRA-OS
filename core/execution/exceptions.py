class ExecutionServiceError(Exception):
    """Base exception for the Execution Service kernel."""
    pass


class ExecutionValidationError(ExecutionServiceError):
    """Raised when an ExecutionCommand is structurally invalid."""
    pass


class ExecutionPermissionDeniedError(ExecutionServiceError):
    """Raised when the Security Kernel denies authorization."""
    pass


class ExecutionRuntimeError(ExecutionServiceError):
    """Raised when the Runtime encounters an unhandled error."""
    pass
