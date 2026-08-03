from typing import Type, TypeVar, List

from .models import Event
from .subscriber import EventHandler
from .publisher import Publisher
from .middleware import Middleware
from .dispatcher import Dispatcher

TEvent = TypeVar("TEvent", bound=Event)

class EventBus(Publisher):
    """
    The kernel communication layer of IRA OS.
    Asynchronous, strongly-typed event bus supporting middleware and isolated dispatching.
    """
    def __init__(self):
        self._dispatcher = Dispatcher()
        self._middlewares: List[Middleware] = []

    def use(self, middleware: Middleware) -> None:
        """Register a middleware to intercept events before dispatch."""
        self._middlewares.append(middleware)

    def subscribe(self, event_type: Type[TEvent], handler: EventHandler) -> None:
        """Subscribe to a strongly typed event."""
        self._dispatcher.subscribe(event_type, handler)

    def unsubscribe(self, event_type: Type[TEvent], handler: EventHandler) -> None:
        """Unsubscribe a previously registered handler."""
        self._dispatcher.unsubscribe(event_type, handler)

    async def publish(self, event: Event) -> None:
        """
        Publish an event through the middleware chain, ending with the dispatcher.
        """
        await self._run_middlewares(event, 0)

    async def _run_middlewares(self, event: Event, index: int) -> None:
        if index < len(self._middlewares):
            middleware = self._middlewares[index]
            
            async def next_call(ev: Event) -> None:
                await self._run_middlewares(ev, index + 1)
                
            await middleware(event, next_call)
        else:
            # End of chain, dispatch event
            await self._dispatcher.dispatch(event)
