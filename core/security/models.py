from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping, Optional, Tuple


class TrustLevel(Enum):
    """Defines the required trust tier for a capability request."""
    UNTRUSTED = "UNTRUSTED"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class PermissionState(Enum):
    """The outcome of a permission evaluation."""
    PENDING = "PENDING"
    GRANTED = "GRANTED"
    DENIED = "DENIED"
    REQUIRES_APPROVAL = "REQUIRES_APPROVAL"


@dataclass(frozen=True)
class PermissionRequirement:
    """Declares what trust and approval level a capability requires."""
    capability_id: str
    required_trust_level: TrustLevel
    requires_user_approval: bool = False
    reason: str = ""


@dataclass(frozen=True)
class PermissionPolicy:
    """An immutable policy governing one or more capabilities."""
    policy_id: str
    name: str
    description: str
    requirements: Tuple[PermissionRequirement, ...] = ()


@dataclass(frozen=True)
class SecurityContext:
    """Contextual information accompanying a permission request."""
    request_id: str
    capability_id: str
    trust_level: TrustLevel = TrustLevel.UNTRUSTED
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PermissionRequest:
    """A request to the Permission Kernel for authorization."""
    permission_id: str
    capability_id: str
    context: SecurityContext
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class PermissionDecision:
    """An intermediate record of the authorization decision reached."""
    permission_id: str
    capability_id: str
    state: PermissionState
    trust_level: TrustLevel
    requires_user_approval: bool = False
    denial_reason: Optional[str] = None


@dataclass(frozen=True)
class PermissionResult:
    """The final, immutable result returned from the Permission Kernel."""
    permission_id: str
    capability_id: str
    granted: bool
    state: PermissionState
    denial_reason: Optional[str] = None
    decided_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class PermissionError:
    """An immutable record of a permission evaluation failure."""
    permission_id: str
    error_message: str
