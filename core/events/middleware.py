from typing import Protocol, Callable, Awaitable
from .models import Event

NextMiddleware = Callable[[Event], Awaitable[None]]

class Middleware(Protocol):
    """
    Protocol for Event Bus middleware.
    Middleware can intercept, modify, or observe events before they reach the dispatcher.
    """
    async def __call__(self, event: Event, next_call: NextMiddleware) -> None:
        """Process the event and optionally call the next middleware."""
        ...
