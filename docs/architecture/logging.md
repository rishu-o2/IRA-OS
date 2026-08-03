# Logging & Telemetry Architecture

## Overview
The Logging subsystem is a kernel-level, structured, non-blocking logging system for IRA OS. It is completely independent of Brain, Memory, Tools, or any application module. It depends only on the Python standard library, the Event Bus (optionally), the Configuration System, and the DI Container.

## Components

### `LogLevel` (`levels.py`)
An `IntEnum` ranging from `TRACE (5)` through `CRITICAL (50)`. Integer comparison enables level filtering with simple numeric operators.

### `LogEntry` (`models.py`)
An immutable `@dataclass(frozen=True)` capturing a structured log event with:
- `timestamp`: UTC datetime of emission
- `level`: `LogLevel`
- `logger`: Dot-separated hierarchical name (e.g., `core.events.bus`)
- `message`: Human-readable description
- `correlation_id`: Optional trace ID propagated from context
- `event_id`: Optional event ID from the Event Bus context
- `exception`: Optional `BaseException` with full traceback support
- `metadata`: Arbitrary key-value dict for structured fields

### Context Propagation (`context.py`)
Uses `contextvars.ContextVar` for coroutine/task-scoped correlation ID tracking. Contexts are stored per-task so different async tasks maintain isolated contexts.
- `LogScope` is a context manager that sets and restores `correlation_id` automatically.
- Works correctly in both async and sync code paths.

### Formatters (`formatters.py`)
Two concrete implementations of the `LogFormatter` protocol:
- `HumanFormatter`: Colorized, human-readable output (ANSI codes). Suitable for development.
- `JsonFormatter`: Serializes each entry as a single JSON line. Suitable for log aggregation pipelines (e.g., Elasticsearch, Datadog).

### Sinks (`sinks.py`)
Concrete implementations of the `LogSink` protocol:
- `NullSink`: Discards everything. Designed for testing.
- `ConsoleSink`: Thread-safe write to stdout/stderr.
- `FileSink`: Thread-safe, buffered file writes with configurable `buffer_size`.

All sinks are thread-safe and pluggable.

### Logger (`logger.py`)
Loggers are named using dot-separated paths (`core.events.bus`). Each logger has:
- A configured minimum `LogLevel`
- Zero or more `LogSink` destinations
- An optional parent `Logger` for hierarchical dispatch

Log events propagate **upward** through the hierarchy: a message emitted by `core.events.bus` will be dispatched to its sinks, then to `core.events`'s sinks, then to `core`'s sinks. This mirrors the Python `logging` module's behavior.

Sink failures are **always suppressed** — the logging system must never block or crash the caller.

### Event Bus Integration
The logger optionally publishes `LogEvent` messages to the `EventBus`. This is:
- Disabled by default
- Fully configurable (opt-in via `publish_log_events=True`)
- Non-blocking: it uses `loop.create_task()` so the caller is never awaited
- Non-circular: the `EventBus` may **inject a logger** via DI, but the logger only holds a reference to the bus, never importing it at module level

### LoggerFactory (`factory.py`)
A thread-safe registry that creates, caches, and correctly parents loggers. Calling `factory.get("core.events.bus")` automatically wires it as a child of `core.events`, which is a child of `core`.

### LoggingModule (`logging_module.py`)
A `Module` implementation (DI Contract) that registers `LoggerFactory` and a root `Logger` into the DI Container. Components should inject `Logger` directly or use the factory to create named sub-loggers.

## Future Extension Points
- **Remote Sinks**: A `GCPCloudLoggingSink` or `DatadogSink` can be added without any changes to the core API.
- **Log Sampling**: A sampling middleware can be added between Logger and Sink dispatch.
- **Async Sinks**: The sink protocol can be extended to support `async def emit()` for truly non-blocking writes.
