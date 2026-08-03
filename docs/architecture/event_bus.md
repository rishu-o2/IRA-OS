# Event Bus Architecture

## Overview
The Event Bus serves as the kernel communication layer of IRA OS, acting as the foundational messaging backbone for all components. To support highly concurrent processing, scaling, and fault tolerance, it abandons the legacy synchronous model in favor of an **async-first** architecture powered by Python's `asyncio`.

## Design Decisions

### 1. Async-First Dispatching
**Why:** The IRA OS needs to handle diverse I/O bound tasks efficiently (network requests, LLM API calls, file parsing). A synchronous Event Bus would block the entire system if a single handler performed heavy I/O.
**How:** We use `asyncio.gather(*tasks, return_exceptions=True)` to dispatch events concurrently. This guarantees that one failing subscriber never blocks others, achieving high resilience.

### 2. Strong Typing vs. String Routing
**Why:** The legacy system routed events based on loose strings, which is error-prone, hard to refactor, and provides poor IDE autocomplete support. 
**How:** The Event Bus leverages Python `Type[Event]` as the routing key. Handlers subscribe to concrete Data Classes inheriting from `Event`. This enforcing strict contracts between publishers and subscribers.

### 3. Modularity and Separation of Concerns
**Why:** A monolithic `bus.py` becomes difficult to maintain as we add middleware, routing algorithms, or specific publisher/subscriber constraints.
**How:** The module is divided into:
- `dispatcher.py`: Solely handles routing logic and isolated execution.
- `middleware.py`: Defines a clean protocol for intercepting events before dispatch (e.g., logging, metrics).
- `models.py`: Defines the strictly typed `Event` with kernel requirements (`event_id`, `timestamp`, `source`, `correlation_id`, `payload`, `metadata`).
- `bus.py`: The orchestrator that wires the `Dispatcher` and `Middleware` together behind a clean Facade interface.

### 4. Resilient Subscriptions
If a handler crashes, the `Dispatcher` logs the exception but allows the rest of the ecosystem to continue functioning. The core operating system must not go down due to an application-layer plugin fault.
