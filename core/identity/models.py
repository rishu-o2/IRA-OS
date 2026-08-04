from dataclasses import dataclass, field
from datetime import datetime, timezone
from types import MappingProxyType
from typing import Any, Mapping, Optional, Tuple
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
    roles: Tuple[Role, ...] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    active: bool = True

    def __post_init__(self) -> None:
        roles = tuple(self.roles or ())
        metadata = self.metadata or {}
        if not isinstance(metadata, MappingProxyType):
            metadata = MappingProxyType(dict(metadata))
        object.__setattr__(self, "roles", roles)
        object.__setattr__(self, "metadata", metadata)


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
