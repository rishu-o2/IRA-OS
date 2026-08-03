import sys
import io
import threading
from typing import Protocol, TextIO
from .models import LogEntry
from .formatters import LogFormatter, HumanFormatter
from .exceptions import SinkError


class LogSink(Protocol):
    """Protocol for log sinks. All sinks are synchronous for simplicity."""
    def emit(self, entry: LogEntry) -> None:
        """Write a formatted LogEntry to this sink's output destination."""
        ...

    def flush(self) -> None:
        """Flush any buffered output."""
        ...

    def close(self) -> None:
        """Release any resources held by this sink."""
        ...


class NullSink:
    """
    A no-op sink for testing environments.
    Discards all log entries silently.
    """
    def emit(self, entry: LogEntry) -> None:
        pass

    def flush(self) -> None:
        pass

    def close(self) -> None:
        pass


class ConsoleSink:
    """
    Writes formatted log entries to stdout or stderr.
    Thread-safe via an internal lock.
    """
    def __init__(self, formatter: LogFormatter | None = None, stream: TextIO | None = None):
        self._formatter = formatter or HumanFormatter(colorize=True)
        self._stream = stream or sys.stdout
        self._lock = threading.Lock()

    def emit(self, entry: LogEntry) -> None:
        try:
            line = self._formatter.format(entry)
            with self._lock:
                self._stream.write(line + "\n")
        except Exception as e:
            raise SinkError(f"ConsoleSink failed to emit: {e}") from e

    def flush(self) -> None:
        with self._lock:
            self._stream.flush()

    def close(self) -> None:
        self.flush()


class FileSink:
    """
    Writes formatted log entries to a file in a buffered, thread-safe manner.
    """
    def __init__(
        self,
        filepath: str,
        formatter: LogFormatter | None = None,
        buffer_size: int = 8192,
        mode: str = "a",
        encoding: str = "utf-8"
    ):
        self._formatter = formatter or HumanFormatter(colorize=False)
        self._filepath = filepath
        self._lock = threading.Lock()
        try:
            self._file = io.open(filepath, mode=mode, encoding=encoding, buffering=buffer_size)
        except OSError as e:
            raise SinkError(f"FileSink could not open '{filepath}': {e}") from e

    def emit(self, entry: LogEntry) -> None:
        try:
            line = self._formatter.format(entry)
            with self._lock:
                self._file.write(line + "\n")
        except Exception as e:
            raise SinkError(f"FileSink failed to emit to '{self._filepath}': {e}") from e

    def flush(self) -> None:
        with self._lock:
            self._file.flush()

    def close(self) -> None:
        with self._lock:
            self._file.flush()
            self._file.close()
