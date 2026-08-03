import asyncio
import logging
from collections import defaultdict
from typing import Type, TypeVar, Any

from .models import Event
from .subscriber import EventHandler
from .exceptions import DispatchError

logger = logging.getLogger(__name__)

TEvent = TypeVar("TEvent", bound=Event)

class Dispatcher:
    """
    Routes events to registered subscribers asynchronously.
    Guarantees that one failing subscriber does not block others.
    """
    def __init__(self):
        # Maps exact event type to a set of handlers
        self._subscribers: dict[Type[Event], set[EventHandler]] = defaultdict(set)
        # Catch-all or base type handlers
        self._wildcard_subscribers: set[EventHandler] = set()

    def subscribe(self, event_type: Type[TEvent], handler: EventHandler) -> None:
        """Register a handler for a specific event type."""
        if event_type is Event:
            self._wildcard_subscribers.add(handler)
        else:
            self._subscribers[event_type].add(handler)

    def unsubscribe(self, event_type: Type[TEvent], handler: EventHandler) -> None:
        """Unregister a handler."""
        if event_type is Event:
            self._wildcard_subscribers.discard(handler)
        else:
            self._subscribers[event_type].discard(handler)

    async def dispatch(self, event: Event) -> None:
        """
        Dispatch the event to all matching subscribers.
        Failing subscribers are isolated and logged.
        """
        handlers = set()
        
        # Exact match handlers
        event_type = type(event)
        if event_type in self._subscribers:
            handlers.update(self._subscribers[event_type])
            
        # Wildcard handlers (subscribed to base Event type)
        handlers.update(self._wildcard_subscribers)

        if not handlers:
            logger.debug(f"No subscribers found for event: {event.name}")
            return

        tasks = [
            self._safe_invoke(handler, event)
            for handler in handlers
        ]
        
        # Run concurrently, isolating failures
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Subscriber failed while processing {event.name}: {result}")
                # We do not raise here because we don't want to block further execution.
                # In the future, we could publish a 'SubscriberFailedEvent' to the bus itself.

    async def _safe_invoke(self, handler: EventHandler, event: Event) -> None:
        try:
            await handler(event)
        except Exception as e:
            raise DispatchError(f"Handler {handler} failed: {e}") from e
