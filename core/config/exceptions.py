class ConfigurationError(Exception):
    """Base exception for configuration-related errors."""
    pass

class ValidationError(ConfigurationError):
    """Raised when configuration fails schema, type, or rule validation."""
    pass

class SecretResolutionError(ConfigurationError):
    """Raised when a secret value cannot be resolved or is missing."""
    pass
