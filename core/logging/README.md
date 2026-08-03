# IRA OS Logging Subsystem

Structured, hierarchical, async-safe logging for IRA OS.

## Quick Start

```python
from core.logging import LoggerFactory, LogLevel, NullSink, ConsoleSink

factory = LoggerFactory(level=LogLevel.DEBUG, sinks=[ConsoleSink()])

logger = factory.get("core.events.bus")
logger.info("Event dispatched", event_type="MockEvent")
logger.error("Handler failed", exception=e)
```

## DI Integration

```python
from core.logging import LoggingModule, LoggerFactory, Logger

module = LoggingModule.from_config(level=LogLevel.INFO, console=True)
container.install(module)

# In a component:
class MyService:
    def __init__(self, factory: LoggerFactory):
        self._log = factory.get("my.service")
```

## Features
- `TRACE`, `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` levels
- Hierarchical loggers with automatic sink propagation
- `HumanFormatter` (colorized) and `JsonFormatter` (production)
- `ConsoleSink`, `FileSink`, `NullSink`
- `LogScope` context manager for `correlation_id` scoping
- Optional Event Bus integration (non-circular, opt-in)
