from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from .levels import LogLevel

@dataclass(frozen=True)
class LogEntry:
    """
    Immutable, structured representation of a single log event.
    This is the core data model that flows through the logging pipeline.
    """
    level: LogLevel
    logger: str
    message: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    correlation_id: str | None = None
    event_id: str | None = None
    exception: BaseException | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        # Validate that metadata is always a dict (can't assign to frozen field,
        # so we check here for safety in non-default code paths)
        if not isinstance(self.metadata, dict):
            object.__setattr__(self, 'metadata', {})
