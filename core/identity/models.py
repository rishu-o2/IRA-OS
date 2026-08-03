from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from core.events.models import Event
from .roles import Role
from .permissions import Permission


@dataclass(frozen=True)
class Identity:
    """Immutable representation of a user, service, or system entity."""
    id: str
    username: str
    display_name: str
    email: Optional[str] = None
    roles: List[Role] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    active: bool = True


# --- Events ---

@dataclass(frozen=True, kw_only=True)
class IdentityRegistered(Event):
    """Published when a new identity is registered."""
    identity_id: str
    username: str

    @property
    def name(self) -> str:
        return "IdentityRegistered"


@dataclass(frozen=True, kw_only=True)
class IdentityAuthenticated(Event):
    """Published when a session is successfully authenticated."""
    identity_id: str
    session_id: str

    @property
    def name(self) -> str:
        return "IdentityAuthenticated"


@dataclass(frozen=True, kw_only=True)
class IdentityLoggedOut(Event):
    """Published when a session is logged out."""
    identity_id: str
    session_id: str

    @property
    def name(self) -> str:
        return "IdentityLoggedOut"


@dataclass(frozen=True, kw_only=True)
class PermissionGranted(Event):
    """Published when a permission is explicitly granted to an identity."""
    identity_id: str
    permission: str

    @property
    def name(self) -> str:
        return "PermissionGranted"


@dataclass(frozen=True, kw_only=True)
class PermissionRevoked(Event):
    """Published when a permission is explicitly revoked from an identity."""
    identity_id: str
    permission: str

    @property
    def name(self) -> str:
        return "PermissionRevoked"
