import json
import traceback
from typing import Protocol
from .models import LogEntry
from .exceptions import FormatterError


class LogFormatter(Protocol):
    """Protocol for log formatters."""
    def format(self, entry: LogEntry) -> str:
        """Render a LogEntry to a string."""
        ...


class HumanFormatter:
    """
    Formats log entries as human-readable, colorized text.
    Suitable for development consoles.
    """
    # ANSI color codes
    _LEVEL_COLORS = {
        5:  "\033[90m",   # TRACE  - dark gray
        10: "\033[36m",   # DEBUG  - cyan
        20: "\033[32m",   # INFO   - green
        30: "\033[33m",   # WARNING - yellow
        40: "\033[31m",   # ERROR  - red
        50: "\033[1;31m", # CRITICAL - bold red
    }
    _RESET = "\033[0m"

    def __init__(self, colorize: bool = True):
        self._colorize = colorize

    def format(self, entry: LogEntry) -> str:
        ts = entry.timestamp.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        level_str = str(entry.level).ljust(8)

        if self._colorize:
            color = self._LEVEL_COLORS.get(int(entry.level), "")
            level_str = f"{color}{level_str}{self._RESET}"

        ctx_parts = []
        if entry.correlation_id:
            ctx_parts.append(f"cid={entry.correlation_id[:8]}")
        if entry.event_id:
            ctx_parts.append(f"eid={entry.event_id[:8]}")
        ctx_str = f" [{', '.join(ctx_parts)}]" if ctx_parts else ""

        line = f"{ts} {level_str} {entry.logger}{ctx_str}: {entry.message}"

        if entry.exception:
            tb = "".join(traceback.format_exception(
                type(entry.exception), entry.exception, entry.exception.__traceback__
            ))
            line += f"\n{tb.rstrip()}"

        if entry.metadata:
            meta_str = "  ".join(f"{k}={v}" for k, v in entry.metadata.items())
            line += f" | {meta_str}"

        return line


class JsonFormatter:
    """
    Formats log entries as JSON lines.
    Suitable for production log aggregation pipelines.
    """
    def format(self, entry: LogEntry) -> str:
        payload = {
            "timestamp": entry.timestamp.isoformat(),
            "level": str(entry.level),
            "logger": entry.logger,
            "message": entry.message,
        }

        if entry.correlation_id:
            payload["correlation_id"] = entry.correlation_id
        if entry.event_id:
            payload["event_id"] = entry.event_id
        if entry.metadata:
            payload["metadata"] = entry.metadata
        if entry.exception:
            payload["exception"] = {
                "type": type(entry.exception).__name__,
                "message": str(entry.exception),
                "traceback": "".join(traceback.format_exception(
                    type(entry.exception), entry.exception, entry.exception.__traceback__
                ))
            }

        try:
            return json.dumps(payload, default=str)
        except Exception as e:
            raise FormatterError(f"Failed to serialize LogEntry to JSON: {e}") from e
