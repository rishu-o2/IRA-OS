from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping, Optional


class ExecutionOutcomeStatus(Enum):
    """The final status of an execution attempt."""
    SUCCEEDED = "SUCCEEDED"
    DENIED = "DENIED"
    FAILED = "FAILED"


@dataclass(frozen=True)
class ExecutionCommand:
    """
    An immutable command describing a single capability execution request.

    The ExecutionCommand is the canonical input to the ExecutionService.
    It carries the capability identifier, arguments, and a unique command ID
    for correlation through the execution pipeline.
    """
    command_id: str
    capability_id: str
    arguments: Mapping[str, Any] = field(default_factory=dict)
    metadata: Mapping[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class ExecutionOutcome:
    """
    An immutable result returned by the ExecutionService.

    The ExecutionOutcome carries the final status, optional result data,
    and optional denial/failure reason for traceability.
    """
    command_id: str
    capability_id: str
    status: ExecutionOutcomeStatus
    result_data: Optional[Any] = None
    denial_reason: Optional[str] = None
    error: Optional[str] = None
    completed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def succeeded(self) -> bool:
        return self.status == ExecutionOutcomeStatus.SUCCEEDED

    @property
    def denied(self) -> bool:
        return self.status == ExecutionOutcomeStatus.DENIED

    @property
    def failed(self) -> bool:
        return self.status == ExecutionOutcomeStatus.FAILED
