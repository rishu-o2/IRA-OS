from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping, Optional, Tuple


class ExecutionStatus(Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass(frozen=True)
class CapabilityMetadata:
    id: str
    name: str
    description: str
    version: str


@dataclass(frozen=True)
class ExecutionRequest:
    execution_id: str
    capability_id: str
    arguments: Mapping[str, Any] = field(default_factory=dict)
    metadata: Mapping[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class ExecutionResult:
    execution_id: str
    success: bool
    status: ExecutionStatus
    result_data: Optional[Any] = None
    error: Optional[str] = None
    completed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class ExecutionContext:
    request: ExecutionRequest
    capability_metadata: CapabilityMetadata


@dataclass(frozen=True)
class ExecutionError:
    execution_id: str
    error_message: str
