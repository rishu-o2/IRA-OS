class SecurityError(Exception):
    """Base exception for the Permission & Security subsystem."""
    pass


class PermissionValidationError(SecurityError):
    """Raised when a PermissionRequest is malformed or invalid."""
    pass


class PolicyNotFoundError(SecurityError):
    """Raised when no applicable policy is found for a capability."""
    pass


class PermissionDeniedError(SecurityError):
    """Raised when authorization is explicitly denied."""
    pass


class PolicyEvaluationError(SecurityError):
    """Raised when policy evaluation encounters an unrecoverable error."""
    pass
