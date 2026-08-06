class AndroidRuntimeError(Exception):
    """Base exception for the Android Runtime subsystem."""
    pass

class AndroidAdapterError(AndroidRuntimeError):
    """Raised when the Android Adapter fails to translate or route a capability request."""
    pass

class AndroidCapabilityRegistrationError(AndroidRuntimeError):
    """Raised when there is an issue registering or discovering an Android capability."""
    pass
