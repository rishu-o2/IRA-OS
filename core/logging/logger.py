from typing import Any, TYPE_CHECKING
from .levels import LogLevel
from .models import LogEntry
from .sinks import LogSink, NullSink
from .context import get_context

if TYPE_CHECKING:
    from core.events import EventBus


class Logger:
    """
    Hierarchical, structured logger.

    Loggers are named using dot-separated paths (e.g., 'core.events.bus').
    A child logger inherits the effective level from its parent if its own
    level is not explicitly set.

    Log entries are dispatched synchronously to all registered sinks.
    Sink failures are swallowed silently to guarantee non-blocking operation.

    Event Bus integration is optional and fully decoupled.
    """

    def __init__(
        self,
        name: str,
        level: LogLevel = LogLevel.DEBUG,
        sinks: list[LogSink] | None = None,
        parent: 'Logger | None' = None,
        event_bus: Any | None = None,
        publish_log_events: bool = False,
    ):
        self.name = name
        self._level = level
        self._sinks: list[LogSink] = sinks or []
        self._parent = parent
        self._event_bus = event_bus
        self._publish_log_events = publish_log_events

    @property
    def effective_level(self) -> LogLevel:
        """Walk up the hierarchy to find the effective minimum log level."""
        if self._level is not None:
            return self._level
        if self._parent:
            return self._parent.effective_level
        return LogLevel.DEBUG

    def set_level(self, level: LogLevel) -> None:
        self._level = level

    def add_sink(self, sink: LogSink) -> None:
        self._sinks.append(sink)

    def _dispatch(self, entry: LogEntry) -> None:
        """Dispatch a log entry to all sinks. Sink failures are suppressed."""
        for sink in self._sinks:
            try:
                sink.emit(entry)
            except Exception:
                pass  # Never let a sink failure break the caller

        # Optionally propagate to parent sinks (hierarchical dispatch)
        if self._parent:
            self._parent._dispatch(entry)

    def _build_entry(
        self,
        level: LogLevel,
        message: str,
        exception: BaseException | None = None,
        **metadata: Any
    ) -> LogEntry:
        ctx = get_context()
        return LogEntry(
            level=level,
            logger=self.name,
            message=message,
            correlation_id=ctx.correlation_id,
            event_id=ctx.event_id,
            exception=exception,
            metadata=metadata if metadata else {}
        )

    def _log(self, level: LogLevel, message: str, exception: BaseException | None = None, **metadata: Any) -> None:
        if level < self.effective_level:
            return
        entry = self._build_entry(level, message, exception, **metadata)
        self._dispatch(entry)

        # Optional non-blocking event bus publish
        if self._publish_log_events and self._event_bus:
            try:
                import asyncio
                loop = None
                try:
                    loop = asyncio.get_running_loop()
                except RuntimeError:
                    pass

                if loop and loop.is_running():
                    loop.create_task(self._publish_to_bus(entry))
            except Exception:
                pass  # Never block logging due to event bus failures

    async def _publish_to_bus(self, entry: LogEntry) -> None:
        if self._event_bus:
            try:
                from core.events.models import Event
                from datetime import datetime, timezone
                import uuid

                class LogEvent(Event):
                    pass

                log_event = LogEvent(
                    source=entry.logger,
                    payload={"level": str(entry.level), "message": entry.message},
                    correlation_id=entry.correlation_id,
                )
                await self._event_bus.publish(log_event)
            except Exception:
                pass

    # Convenience methods for each log level

    def trace(self, message: str, **metadata: Any) -> None:
        self._log(LogLevel.TRACE, message, **metadata)

    def debug(self, message: str, **metadata: Any) -> None:
        self._log(LogLevel.DEBUG, message, **metadata)

    def info(self, message: str, **metadata: Any) -> None:
        self._log(LogLevel.INFO, message, **metadata)

    def warning(self, message: str, **metadata: Any) -> None:
        self._log(LogLevel.WARNING, message, **metadata)

    def error(self, message: str, exception: BaseException | None = None, **metadata: Any) -> None:
        self._log(LogLevel.ERROR, message, exception, **metadata)

    def critical(self, message: str, exception: BaseException | None = None, **metadata: Any) -> None:
        self._log(LogLevel.CRITICAL, message, exception, **metadata)

    def child(self, suffix: str) -> 'Logger':
        """Create a child logger that inherits this logger's sinks and level."""
        return Logger(
            name=f"{self.name}.{suffix}",
            level=self._level,
            sinks=[],  # Child dispatches upwards to parent
            parent=self,
            event_bus=self._event_bus,
            publish_log_events=self._publish_log_events,
        )
