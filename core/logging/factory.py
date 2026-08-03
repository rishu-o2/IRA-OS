import threading
from typing import Any
from .logger import Logger
from .levels import LogLevel
from .sinks import LogSink, ConsoleSink, NullSink
from .formatters import HumanFormatter, JsonFormatter


class LoggerFactory:
    """
    Registry and factory for named loggers.

    Creates loggers on demand, caches them by name, and builds proper
    parent-child relationships based on dot-separated naming.

    Example:
        factory.get("core")          # root logger for 'core'
        factory.get("core.events")   # child of 'core'
        factory.get("core.events.bus") # child of 'core.events'
    """

    def __init__(
        self,
        level: LogLevel = LogLevel.DEBUG,
        sinks: list[LogSink] | None = None,
        event_bus: Any | None = None,
        publish_log_events: bool = False,
    ):
        self._default_level = level
        self._default_sinks: list[LogSink] = sinks or [ConsoleSink()]
        self._event_bus = event_bus
        self._publish_log_events = publish_log_events
        self._loggers: dict[str, Logger] = {}
        self._lock = threading.Lock()

    def _find_parent(self, name: str) -> Logger | None:
        """Find the nearest existing parent logger by walking up the hierarchy."""
        parts = name.rsplit('.', 1)
        if len(parts) == 1:
            return None  # No parent — this is a root logger
        parent_name = parts[0]
        # Walk up recursively
        if parent_name in self._loggers:
            return self._loggers[parent_name]
        return self._find_parent(parent_name)

    def get(self, name: str) -> Logger:
        """
        Get or create a named logger.
        Logger hierarchy is automatically wired based on the dot-separated name.
        """
        with self._lock:
            if name in self._loggers:
                return self._loggers[name]

            parent = self._find_parent(name)

            if parent is None:
                # Root-level logger receives the default sinks
                logger = Logger(
                    name=name,
                    level=self._default_level,
                    sinks=list(self._default_sinks),
                    event_bus=self._event_bus,
                    publish_log_events=self._publish_log_events,
                )
            else:
                # Child loggers inherit via parent chain, not direct sinks
                logger = Logger(
                    name=name,
                    level=self._default_level,
                    sinks=[],
                    parent=parent,
                    event_bus=self._event_bus,
                    publish_log_events=self._publish_log_events,
                )

            self._loggers[name] = logger
            return logger

    def set_level(self, name: str, level: LogLevel) -> None:
        """Override the level of a specific named logger."""
        logger = self.get(name)
        logger.set_level(level)

    def add_sink(self, name: str, sink: LogSink) -> None:
        """Add a sink to a specific named logger."""
        logger = self.get(name)
        logger.add_sink(sink)
