class EventBusError(Exception):
    """Base exception for all Event Bus related errors."""
    pass

class SubscriberError(EventBusError):
    """Raised when a subscriber fails to process an event."""
    pass

class DispatchError(EventBusError):
    """Raised when the dispatcher fails to route an event."""
    pass
