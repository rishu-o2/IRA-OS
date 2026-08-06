from dataclasses import dataclass
from typing import Any, Mapping

from core.events import Event


@dataclass(frozen=True, kw_only=True)
class WorkflowStarted(Event):
    workflow_id: str


@dataclass(frozen=True, kw_only=True)
class WorkflowCompleted(Event):
    workflow_id: str
    result_data: Mapping[str, Any]


@dataclass(frozen=True, kw_only=True)
class WorkflowFailed(Event):
    workflow_id: str
    error: str


@dataclass(frozen=True, kw_only=True)
class WorkflowCancelled(Event):
    workflow_id: str


@dataclass(frozen=True, kw_only=True)
class WorkflowPaused(Event):
    workflow_id: str


@dataclass(frozen=True, kw_only=True)
class WorkflowResumed(Event):
    workflow_id: str


@dataclass(frozen=True, kw_only=True)
class TaskQueued(Event):
    task_id: str
    workflow_id: str


@dataclass(frozen=True, kw_only=True)
class TaskStarted(Event):
    task_id: str
    workflow_id: str


@dataclass(frozen=True, kw_only=True)
class TaskCompleted(Event):
    task_id: str
    workflow_id: str


@dataclass(frozen=True, kw_only=True)
class TaskFailed(Event):
    task_id: str
    workflow_id: str
    error: str


@dataclass(frozen=True, kw_only=True)
class RetryScheduled(Event):
    task_id: str
    workflow_id: str
    retry_count: int
    delay_ms: int
