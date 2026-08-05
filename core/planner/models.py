from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from types import MappingProxyType
from typing import Any, Iterable, List, Mapping

from .enums import GoalState, TaskState, Priority
from .exceptions import GoalError, TaskError


def _normalize_metadata(metadata: Mapping[str, Any] | None) -> Mapping[str, Any]:
    if metadata is None:
        return {}
    return dict(metadata)


@dataclass(frozen=True)
class Goal:
    id: str
    title: str
    description: str = ""
    priority: Priority = Priority.NORMAL
    state: GoalState = GoalState.NEW
    metadata: Mapping[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        if not self.id:
            raise GoalError("Goal.id must not be empty.")
        if not self.title:
            raise GoalError("Goal.title must not be empty.")
        object.__setattr__(self, "metadata", _normalize_metadata(self.metadata))

    def with_state(self, state: GoalState) -> "Goal":
        return replace(self, state=state, updated_at=datetime.now(timezone.utc))

    def with_update(self, **kwargs: Any) -> "Goal":
        return replace(self, **kwargs, updated_at=datetime.now(timezone.utc))


@dataclass(frozen=True)
class Task:
    id: str
    goal_id: str
    name: str
    description: str = ""
    dependencies: tuple[str, ...] = field(default_factory=tuple)
    priority: Priority = Priority.NORMAL
    state: TaskState = TaskState.PENDING
    retries: int = 0
    metadata: Mapping[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        if not self.id:
            raise TaskError("Task.id must not be empty.")
        if not self.goal_id:
            raise TaskError("Task.goal_id must not be empty.")
        if not self.name:
            raise TaskError("Task.name must not be empty.")
        object.__setattr__(self, "dependencies", tuple(self.dependencies))
        object.__setattr__(self, "metadata", _normalize_metadata(self.metadata))

    def with_state(self, state: TaskState) -> "Task":
        return replace(self, state=state, updated_at=datetime.now(timezone.utc))

    def with_retries(self, retries: int) -> "Task":
        if retries < 0:
            raise TaskError("Retries must not be negative.")
        return replace(self, retries=retries, updated_at=datetime.now(timezone.utc))

    def with_update(self, **kwargs: Any) -> "Task":
        return replace(self, **kwargs, updated_at=datetime.now(timezone.utc))


@dataclass(frozen=True)
class ExecutionPlan:
    goal: Goal
    tasks: tuple[Task, ...]
    graph: Mapping[str, tuple[str, ...]]
    estimated_steps: int
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        immutable_graph = MappingProxyType({task_id: tuple(deps) for task_id, deps in self.graph.items()})
        object.__setattr__(self, "graph", immutable_graph)


@dataclass(frozen=True)
class PlanResult:
    success: bool
    plan: ExecutionPlan | None = None
    error: str | None = None
    completed_tasks: tuple[str, ...] = field(default_factory=tuple)
    failed_tasks: tuple[str, ...] = field(default_factory=tuple)
