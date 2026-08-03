from dataclasses import dataclass, field
from datetime import datetime, timezone
import uuid
from typing import Any

@dataclass(frozen=True)
class Event:
    """
    Base Event model.
    Every event must contain standard kernel fields.
    """
    payload: dict[str, Any]
    source: str
    metadata: dict[str, Any] = field(default_factory=dict)
    
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    correlation_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def name(self) -> str:
        """Return the strong type name of the event."""
        return self.__class__.__name__
