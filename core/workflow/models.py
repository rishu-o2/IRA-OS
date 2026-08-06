from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Mapping, Optional


class WorkflowStatus(Enum):
    """Overall status of a workflow."""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class WorkflowState(Enum):
    """State machine representation for workflows."""
    CREATED = "CREATED"
    QUEUED = "QUEUED"
    EXECUTING = "EXECUTING"
    WAITING = "WAITING"
    TERMINATED = "TERMINATED"


class TaskPriority(Enum):
    """Priority levels for task scheduling."""
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass(frozen=True)
class RetryPolicy:
    """Defines retry behavior for failed tasks."""
    max_retries: int = 0
    backoff_ms: int = 0
    exponential_backoff: bool = False


@dataclass(frozen=True)
class Schedule:
    """Defines timing constraints for task execution."""
    delayed_until: Optional[datetime] = None
    recurring_interval_ms: Optional[int] = None
    cron_expression: Optional[str] = None


@dataclass(frozen=True)
class WorkflowContext:
    """Execution context spanning multiple steps."""
    workflow_id: str
    metadata: Mapping[str, Any] = field(default_factory=dict)
    state_data: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class WorkflowRequest:
    """A request to initiate a new workflow or task."""
    workflow_id: str
    target_capability: str
    arguments: Mapping[str, Any] = field(default_factory=dict)
    priority: TaskPriority = TaskPriority.NORMAL
    schedule: Optional[Schedule] = None
    retry_policy: Optional[RetryPolicy] = None


@dataclass(frozen=True)
class WorkflowTask:
    """An individual unit of work within the workflow engine."""
    task_id: str
    workflow_id: str
    target_capability: str
    arguments: Mapping[str, Any]
    priority: TaskPriority
    status: WorkflowStatus = WorkflowStatus.PENDING
    retry_count: int = 0


@dataclass(frozen=True)
class WorkflowStep:
    """A step inside a larger workflow definition."""
    step_id: str
    task: WorkflowTask
    depends_on: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class ExecutionHistory:
    """Immutable record of task execution events."""
    task_id: str
    events: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class WorkflowResult:
    """The final result of a workflow execution."""
    workflow_id: str
    success: bool
    status: WorkflowStatus
    result_data: Optional[Any] = None
    error: Optional[str] = None
    completed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
