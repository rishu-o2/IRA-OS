import asyncio
from typing import Any
from dataclasses import dataclass
from core.events import EventBus, Event, Middleware

@dataclass(frozen=True)
class MockEvent(Event):
    pass

@dataclass(frozen=True)
class AnotherEvent(Event):
    pass

def test_event_bus_dispatch_exact_type():
    bus = EventBus()
    received = []

    async def handler(event: MockEvent):
        received.append(event)

    bus.subscribe(MockEvent, handler)

    evt = MockEvent(payload={"data": 1}, source="test")
    
    async def run_test():
        await bus.publish(evt)
        assert len(received) == 1
        assert received[0] is evt
        
        # Another event should not trigger
        await bus.publish(AnotherEvent(payload={}, source="test"))
        assert len(received) == 1

    asyncio.run(run_test())

def test_event_bus_dispatch_wildcard():
    bus = EventBus()
    received = []

    async def wildcard_handler(event: Event):
        received.append(event)

    bus.subscribe(Event, wildcard_handler)

    evt1 = MockEvent(payload={"data": 1}, source="test")
    evt2 = AnotherEvent(payload={}, source="test")

    async def run_test():
        await bus.publish(evt1)
        await bus.publish(evt2)

        assert len(received) == 2
        assert received[0] is evt1
        assert received[1] is evt2

    asyncio.run(run_test())

def test_event_bus_isolation():
    bus = EventBus()
    received = []

    async def failing_handler(event: Event):
        raise ValueError("I failed")

    async def successful_handler(event: Event):
        received.append(event)

    bus.subscribe(MockEvent, failing_handler)
    bus.subscribe(MockEvent, successful_handler)

    evt = MockEvent(payload={"data": 1}, source="test")
    
    async def run_test():
        # Publish should not raise an exception, the bus should isolate it
        await bus.publish(evt)
        assert len(received) == 1
        assert received[0] is evt

    asyncio.run(run_test())

def test_event_bus_middleware():
    bus = EventBus()
    received = []
    middleware_log = []

    class LoggingMiddleware:
        async def __call__(self, event: Event, next_call: Any):
            middleware_log.append(f"Before: {event.name}")
            await next_call(event)
            middleware_log.append(f"After: {event.name}")

    bus.use(LoggingMiddleware())

    async def handler(event: MockEvent):
        received.append(event)
        
    bus.subscribe(MockEvent, handler)

    async def run_test():
        await bus.publish(MockEvent(payload={}, source="test"))
        assert len(received) == 1
        assert middleware_log == ["Before: MockEvent", "After: MockEvent"]

    asyncio.run(run_test())
