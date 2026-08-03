from typing import Protocol
from .models import Event

class Publisher(Protocol):
    """
    Protocol for publishing events.
    """
    async def publish(self, event: Event) -> None:
        """Publish an event asynchronously."""
        ...
