class PluginError(Exception):
    """Base exception for the Plugin Framework subsystem."""
    pass


class PluginValidationError(PluginError):
    """Raised when a plugin manifest or metadata is invalid."""
    pass


class PluginLoadError(PluginError):
    """Raised when a plugin fails to load."""
    pass


class PluginNotFoundError(PluginError):
    """Raised when a requested plugin is not found in the registry."""
    pass


class PluginStateError(PluginError):
    """Raised when a plugin transition is invalid for its current state."""
    pass
