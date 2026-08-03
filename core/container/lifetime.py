from enum import Enum, auto

class Lifetime(Enum):
    """
    Defines the lifetime of a service within the Dependency Injection Container.
    """
    SINGLETON = auto()
    """One instance per application."""
    
    SCOPED = auto()
    """One instance per explicit Scope object."""
    
    TRANSIENT = auto()
    """A new instance is created every time it is resolved."""
