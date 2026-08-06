from dataclasses import dataclass
from core.events import Event
from .models import PermissionState, TrustLevel


@dataclass(frozen=True, kw_only=True)
class PermissionRequested(Event):
    """Published when a PermissionRequest enters the kernel."""
    permission_id: str
    capability_id: str


@dataclass(frozen=True, kw_only=True)
class PermissionGranted(Event):
    """Published when a capability is authorized."""
    permission_id: str
    capability_id: str
    trust_level: TrustLevel


@dataclass(frozen=True, kw_only=True)
class PermissionDenied(Event):
    """Published when a capability is refused authorization."""
    permission_id: str
    capability_id: str
    denial_reason: str


@dataclass(frozen=True, kw_only=True)
class PolicyLoaded(Event):
    """Published when a policy is loaded into the evaluator."""
    policy_id: str
    policy_name: str


@dataclass(frozen=True, kw_only=True)
class PolicyEvaluationCompleted(Event):
    """Published after policy evaluation resolves a decision."""
    permission_id: str
    capability_id: str
    state: PermissionState
