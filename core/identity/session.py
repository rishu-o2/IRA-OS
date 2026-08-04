from dataclasses import dataclass, field
from datetime import datetime
from types import MappingProxyType
from typing import Any, Mapping, Optional


@dataclass(frozen=True)
class Session:
    """Immutable representation of an active session."""
    session_id: str
    identity_id: str
    device_id: Optional[str]
    started_at: datetime
    expires_at: Optional[datetime]
    authenticated: bool
    metadata: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))

    def __post_init__(self) -> None:
        metadata = self.metadata or {}
        if not isinstance(metadata, MappingProxyType):
            metadata = MappingProxyType(dict(metadata))
        object.__setattr__(self, "metadata", metadata)
