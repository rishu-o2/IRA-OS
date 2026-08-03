from typing import Any
from .factory import LoggerFactory
from .logger import Logger
from .levels import LogLevel
from .sinks import ConsoleSink, FileSink, NullSink, LogSink
from .formatters import HumanFormatter, JsonFormatter, LogFormatter
from core.container import Module, ContainerProtocol


class LoggingModule(Module):
    """
    DI Container module for the Logging subsystem.

    Registers:
    - LoggerFactory (singleton)
    - A root Logger instance for direct injection

    Usage:
        container.install(LoggingModule(factory))
    """
    def __init__(self, factory: LoggerFactory):
        self._factory = factory

    def configure(self, container: ContainerProtocol) -> None:
        container.register_instance(LoggerFactory, self._factory)
        container.register_instance(Logger, self._factory.get("ira"))

    @classmethod
    def from_config(
        cls,
        level: LogLevel = LogLevel.INFO,
        formatter_type: str = "human",
        console: bool = True,
        file_path: str | None = None,
        event_bus: Any | None = None,
        publish_log_events: bool = False,
    ) -> 'LoggingModule':
        """
        Convenience factory method to build a LoggingModule from plain parameters.
        Typically called by the boot sequence using values from ConfigurationManager.
        """
        sinks: list[LogSink] = []

        if formatter_type == "json":
            formatter: LogFormatter = JsonFormatter()
        else:
            formatter = HumanFormatter(colorize=console)

        if console:
            sinks.append(ConsoleSink(formatter=formatter))

        if file_path:
            sinks.append(FileSink(filepath=file_path, formatter=HumanFormatter(colorize=False)))

        if not sinks:
            sinks.append(NullSink())

        factory = LoggerFactory(
            level=level,
            sinks=sinks,
            event_bus=event_bus,
            publish_log_events=publish_log_events,
        )

        return cls(factory)
