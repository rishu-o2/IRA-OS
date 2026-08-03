from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional

@dataclass(frozen=True)
class Session:
    """Immutable representation of an active session."""
    session_id: str
    identity_id: str
    device_id: Optional[str]
    started_at: datetime
    expires_at: Optional[datetime]
    authenticated: bool
    metadata: Dict[str, Any] = field(default_factory=dict)
