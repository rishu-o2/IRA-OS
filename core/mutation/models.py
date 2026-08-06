from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping, Optional


class MutationState(Enum):
    """The lifecycle state of a mutation."""
    REQUESTED = "REQUESTED"
    WAITING_CONFIRMATION = "WAITING_CONFIRMATION"
    CONFIRMED = "CONFIRMED"
    EXECUTING = "EXECUTING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    ROLLING_BACK = "ROLLING_BACK"
    ROLLED_BACK = "ROLLED_BACK"
    REJECTED = "REJECTED"


class ConfirmationLevel(Enum):
    """The required level of confirmation for a mutation."""
    NONE = "NONE"
    USER = "USER"
    PIN = "PIN"
    BIOMETRIC = "BIOMETRIC"
    OWNER_ONLY = "OWNER_ONLY"


@dataclass(frozen=True)
class MutationMetadata:
    """
    Capability-level metadata describing mutation properties.
    Belongs with the capability definition, not the runtime execution layer.
    """
    is_destructive: bool = False
    supports_rollback: bool = False
    idempotent: bool = False
    audit_required: bool = True
    confirmation_level: ConfirmationLevel = ConfirmationLevel.NONE
    estimated_duration_ms: Optional[int] = None
    side_effects: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class MutationContext:
    """
    Context that follows a mutation through its entire lifecycle.
    """
    mutation_id: str
    workflow_id: Optional[str]
    execution_id: str
    capability_id: str
    user_id: Optional[str] = None
    confirmation_token: Optional[str] = None
    audit_id: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class AuditRecord:
    """
    Immutable record of a mutation, sent to pluggable AuditSinks.
    """
    audit_id: str
    mutation_id: str
    capability_id: str
    action: str
    arguments: Mapping[str, Any]
    status: MutationState
    started_at: datetime
    completed_at: Optional[datetime] = None
    result_data: Optional[Any] = None
    error: Optional[str] = None
    workflow_id: Optional[str] = None
    user_id: Optional[str] = None
    
    @property
    def duration_ms(self) -> Optional[int]:
        if not self.completed_at:
            return None
        return int((self.completed_at - self.started_at).total_seconds() * 1000)
