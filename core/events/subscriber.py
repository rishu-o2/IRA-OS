from typing import Protocol, TypeVar, Callable, Awaitable, Any, Type
from .models import Event

TEvent = TypeVar("TEvent", bound=Event)

class Subscriber(Protocol):
    """
    Protocol for an event subscriber.
    Subscribers handle specific event types asynchronously.
    """
    async def __call__(self, event: Event) -> None:
        ...

EventHandler = Callable[[TEvent], Awaitable[None]]
