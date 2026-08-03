class IdentityError(Exception):
    """Base exception for all Identity System errors."""
    pass

class AuthenticationError(IdentityError):
    """Raised when authentication fails."""
    pass

class AuthorizationError(IdentityError):
    """Raised when an identity lacks required permissions."""
    pass

class SessionExpiredError(IdentityError):
    """Raised when a session has expired."""
    pass

class IdentityRegistrationError(IdentityError):
    """Raised on invalid identity registration (e.g. duplicate username)."""
    pass

class SessionRegistrationError(IdentityError):
    """Raised on invalid session registration operations."""
    pass
