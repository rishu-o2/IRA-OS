# Architecture Decision Record 0004: Logging & Telemetry System

## Title
ADR-0004: Structured Logging & Telemetry Architecture

## Status
Accepted

## Date
2026-08-03

## Context
IRA OS requires a production-grade logging subsystem. Application-layer components (Brain, Memory, Tools) and kernel modules (Event Bus, Config, DI) all need the ability to emit observable, structured log events. Standard Python `print()` calls are unacceptable: they are unstructured, unfiltered, and cannot be routed, aggregated, or queried. The Python standard library `logging` module is overly complex, globally stateful, and unsafe in an async-first OS.

## Decision
We implemented a custom, structured, async-safe Logging subsystem within `core/logging/`.

Key design choices:
1. **Structured `LogEntry` model**: Every log event is an immutable dataclass, not a raw string. This enables downstream processing, filtering, and structured storage.
2. **`IntEnum` levels**: Using `IntEnum` for `LogLevel` allows for simple numeric comparisons (`level >= LogLevel.WARNING`) without string-matching or special casing.
3. **Sink abstraction**: The `LogSink` protocol allows plugging in any destination. The default set covers Console, File, and Null (testing). Remote sinks can be added without any changes to the Logger engine.
4. **Human & JSON formatters**: Two formatters cover 100% of use cases (development terminals and production aggregation pipelines).
5. **Hierarchical loggers**: Named with dot-separated paths. Child loggers propagate events to parent sinks, matching developer intuition and enabling namespace-level configuration.
6. **Context Propagation via `contextvars`**: Automatic `correlation_id` tracking across async tasks using `contextvars.ContextVar`. A `LogScope` context manager handles entering and exiting scoped contexts cleanly.
7. **Optional Event Bus integration**: The logger can optionally publish to the Event Bus. This avoids circular imports by using `TYPE_CHECKING` guards and lazy imports. The Event Bus never depends on the logger at the module level.
8. **Sink failure isolation**: Any exception from a sink is caught and suppressed. The logging system must never crash the application.

## Alternatives Considered
- **Python `logging` module**: Rejected. It uses a global handler registry, is not async-safe, and its complexity and edge cases (handler propagation, root logger misuse) make it unsuitable for a controlled OS environment.
- **Third-party libraries (Structlog, Loguru)**: Rejected. External dependencies are forbidden for kernel modules.

## Consequences
- **Positive**: Fully structured, observable, testable, and sink-agnostic logging. Zero external dependencies.
- **Negative**: We maintain our own logging pipeline. New formatter types (e.g., Protobuf) require implementing the `LogFormatter` protocol explicitly.

## Version
v1.3.0
