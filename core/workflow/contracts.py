from abc import ABC, abstractmethod
from typing import List, Optional

from core.lifecycle.models import ComponentHealth

from .models import WorkflowRequest, WorkflowResult, WorkflowStatus, WorkflowTask


class WorkflowScheduler(ABC):
    """Abstract contract for scheduling workflow tasks."""

    @abstractmethod
    def schedule(self, request: WorkflowRequest) -> WorkflowTask:
        """Resolves schedule constraints and creates a scheduled task."""
        pass


class WorkflowQueue(ABC):
    """Abstract contract for task queuing."""

    @abstractmethod
    def enqueue(self, task: WorkflowTask) -> None:
        pass

    @abstractmethod
    def dequeue(self) -> Optional[WorkflowTask]:
        pass

    @abstractmethod
    def peek(self) -> Optional[WorkflowTask]:
        pass

    @abstractmethod
    def remove(self, task_id: str) -> bool:
        pass

    @abstractmethod
    def lookup(self, task_id: str) -> Optional[WorkflowTask]:
        pass

    @abstractmethod
    def status(self) -> dict:
        pass


class WorkflowExecutor(ABC):
    """Abstract contract for orchestrating task execution."""

    @abstractmethod
    async def dispatch(self, task: WorkflowTask) -> Any:
        """Dispatches a task for execution."""
        pass


class WorkflowManager(ABC):
    """
    Abstract contract for the Workflow Engine Manager.
    Orchestrates the canonical workflow pipeline.
    """

    @abstractmethod
    async def start(self) -> None:
        """Start the workflow engine. Must be idempotent."""
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        """Shut down the workflow engine. Must be idempotent."""
        pass

    @abstractmethod
    async def health_check(self) -> ComponentHealth:
        """Return the current health state of the workflow engine."""
        pass

    @abstractmethod
    async def submit(self, request: WorkflowRequest) -> WorkflowResult:
        """Submit a new workflow request for orchestration."""
        pass

    @abstractmethod
    async def cancel(self, workflow_id: str) -> None:
        """Cancel a running or pending workflow."""
        pass

    @abstractmethod
    async def pause(self, workflow_id: str) -> None:
        """Pause a workflow."""
        pass

    @abstractmethod
    async def resume(self, workflow_id: str) -> None:
        """Resume a paused workflow."""
        pass

    @abstractmethod
    async def status(self, workflow_id: str) -> WorkflowStatus:
        """Retrieve the current status of a workflow."""
        pass
