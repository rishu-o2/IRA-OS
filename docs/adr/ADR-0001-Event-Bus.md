# ADR-0001: Event Bus

**Status**: Accepted
**Date**: 2026-08-02
**Version**: v1.0.0

## Context
IRA OS requires a foundational communication layer to facilitate messaging between its components. The legacy `IRA-main` system utilized a synchronous, string-routed event bus. A review of this architecture indicated that a synchronous model would bottleneck the OS due to I/O constraints (e.g., LLM generation, networking), and string-routing was prone to errors without strict contracts.

## Decision
We implemented a strongly typed, async-first Event Bus to serve as the kernel communication layer for IRA OS.

Key design pillars include:
1. **Async-first architecture**: Leverages `asyncio` to handle diverse I/O bound tasks efficiently, guaranteeing that a single subscriber cannot block the main event loop.
2. **Strongly typed events**: Uses Python `Type[Event]` as routing keys and concrete `dataclasses` inheriting from `Event` to enforce strict publisher/subscriber contracts.
3. **Middleware pipeline**: An interceptor pattern (`await middleware(event, next_call)`) allowing cross-cutting concerns like logging, tracing, and metrics to be applied globally.
4. **Event-driven communication**: De-couples subsystems allowing the OS to react dynamically without tightly coupling domains.
5. **Independent kernel module**: The `core/events` module has zero dependencies on business/domain logic (`brain/`, `memory/`, `clients/`, etc.), ensuring it is perfectly isolated and universally usable.

## Alternatives Considered
- *Synchronous Event Bus*: Rejected due to the risk of blocking I/O calls severely degrading OS performance.
- *String-based routing*: Rejected due to poor developer experience, lack of type safety, and IDE autocomplete limitations.
- *Message Brokers (RabbitMQ, Redis)*: Rejected as overkill for the initial kernel layer, though the middleware architecture allows integrating them later for distributed events.

## Consequences
- **Positive**: Components are decoupled; system is non-blocking and resilient to individual handler crashes.
- **Negative**: All subscribers must be `async` functions, and developers must be careful not to introduce synchronous blocking I/O within handlers.

## Future Evolution
The Event Bus is designed to remain stable, with `v1.0.0` being frozen. Future evolutions (like adding configurable concurrency limiters or fixing weak reference retention) are tracked in the Technical Debt register and will be applied iteratively without redesigning the public API.
