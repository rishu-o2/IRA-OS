class CapabilityError(Exception):
    """Base exception for Android Capabilities."""
    pass


class PermissionDeniedError(CapabilityError):
    """Raised when required Android permissions are missing."""
    pass


class ResourceUnavailableError(CapabilityError):
    """Raised when hardware/sensor is missing or busy."""
    pass


class InvalidArgumentError(CapabilityError):
    """Raised when payload fails schema validation."""
    pass


class PlatformExecutionError(CapabilityError):
    """Raised for unhandled native API crashes."""
    pass


class UnsupportedPlatformError(CapabilityError):
    """Raised when a capability cannot run on the current OS."""
    pass
