from typing import Dict

from core.events import EventBus
from core.lifecycle.interfaces import LifecycleComponent
from core.lifecycle.models import ComponentHealth
from core.lifecycle.states import ComponentState
from core.logging import Logger

from .contracts import WorkflowExecutor, WorkflowManager, WorkflowQueue, WorkflowScheduler
from .events import (
    TaskCompleted,
    TaskQueued,
    TaskStarted,
    WorkflowCancelled,
    WorkflowCompleted,
    WorkflowFailed,
    WorkflowPaused,
    WorkflowResumed,
    WorkflowStarted,
)
from .exceptions import WorkflowCancelledError, WorkflowNotFoundError, WorkflowValidationError, WorkflowError
from .models import WorkflowRequest, WorkflowResult, WorkflowStatus


class WorkflowManagerImpl(WorkflowManager, LifecycleComponent):
    """
    Orchestrates the canonical Workflow pipeline:
    1. Validation
    2. Schedule Resolution
    3. Queue Management
    4. Execution Dispatch
    5. Result Normalization
    6. Publish Events
    7. Workflow Result
    """

    def __init__(
        self,
        scheduler: WorkflowScheduler,
        queue: WorkflowQueue,
        executor: WorkflowExecutor,
        event_bus: EventBus,
        logger: Logger,
    ):
        self._scheduler = scheduler
        self._queue = queue
        self._executor = executor
        self._event_bus = event_bus
        self._logger = logger
        self._started = False
        self._statuses: Dict[str, WorkflowStatus] = {}

    async def start(self) -> None:
        if self._started:
            return
        self._logger.info("WorkflowManager starting.")
        self._started = True

    async def shutdown(self) -> None:
        if not self._started:
            return
        self._logger.info("WorkflowManager shutting down.")
        self._started = False

    async def health_check(self) -> ComponentHealth:
        if not self._started:
            return ComponentHealth(state=ComponentState.STOPPED, details="Workflow Engine is stopped.")
        return ComponentHealth(state=ComponentState.RUNNING, details="Workflow Engine is available.")

    async def submit(self, request: WorkflowRequest) -> WorkflowResult:
        if not isinstance(request, WorkflowRequest):
            raise WorkflowValidationError("Invalid request type.")

        self._statuses[request.workflow_id] = WorkflowStatus.PENDING

        try:
            # 1. Validation (passed above)
            
            # 2. Schedule Resolution
            task = self._scheduler.schedule(request)

            # 3. Queue Management
            self._queue.enqueue(task)
            await self._event_bus.publish(TaskQueued(payload={}, task_id=task.task_id, workflow_id=request.workflow_id, source="WorkflowManager"))
            await self._event_bus.publish(WorkflowStarted(payload={}, workflow_id=request.workflow_id, source="WorkflowManager"))
            self._statuses[request.workflow_id] = WorkflowStatus.RUNNING

            # In a real system, a background loop pulls from the queue.
            # For this scaffolding, we synchronously dequeue and dispatch.
            task_to_run = self._queue.dequeue()
            if not task_to_run:
                raise WorkflowError("Queue empty immediately after enqueue.")

            # 4. Execution Dispatch
            await self._event_bus.publish(TaskStarted(payload={}, task_id=task_to_run.task_id, workflow_id=request.workflow_id, source="WorkflowManager"))
            dispatch_result = await self._executor.dispatch(task_to_run)

            # 5. Result Normalization
            await self._event_bus.publish(TaskCompleted(payload={}, task_id=task_to_run.task_id, workflow_id=request.workflow_id, source="WorkflowManager"))
            
            # 6. Publish Events
            await self._event_bus.publish(WorkflowCompleted(payload={}, workflow_id=request.workflow_id, result_data=dispatch_result, source="WorkflowManager"))
            self._statuses[request.workflow_id] = WorkflowStatus.COMPLETED

            # 7. Workflow Result
            return WorkflowResult(
                workflow_id=request.workflow_id,
                success=True,
                status=WorkflowStatus.COMPLETED,
                result_data=dispatch_result,
            )

        except Exception as e:
            self._statuses[request.workflow_id] = WorkflowStatus.FAILED
            await self._event_bus.publish(WorkflowFailed(payload={}, workflow_id=request.workflow_id, error=str(e), source="WorkflowManager"))
            return WorkflowResult(
                workflow_id=request.workflow_id,
                success=False,
                status=WorkflowStatus.FAILED,
                error=str(e),
            )

    async def cancel(self, workflow_id: str) -> None:
        if workflow_id not in self._statuses:
            raise WorkflowNotFoundError(f"Workflow {workflow_id} not found.")
        self._statuses[workflow_id] = WorkflowStatus.CANCELLED
        await self._event_bus.publish(WorkflowCancelled(payload={}, workflow_id=workflow_id, source="WorkflowManager"))

    async def pause(self, workflow_id: str) -> None:
        if workflow_id not in self._statuses:
            raise WorkflowNotFoundError(f"Workflow {workflow_id} not found.")
        self._statuses[workflow_id] = WorkflowStatus.PAUSED
        await self._event_bus.publish(WorkflowPaused(payload={}, workflow_id=workflow_id, source="WorkflowManager"))

    async def resume(self, workflow_id: str) -> None:
        if workflow_id not in self._statuses:
            raise WorkflowNotFoundError(f"Workflow {workflow_id} not found.")
        if self._statuses[workflow_id] == WorkflowStatus.PAUSED:
            self._statuses[workflow_id] = WorkflowStatus.RUNNING
            await self._event_bus.publish(WorkflowResumed(payload={}, workflow_id=workflow_id, source="WorkflowManager"))

    async def status(self, workflow_id: str) -> WorkflowStatus:
        if workflow_id not in self._statuses:
            raise WorkflowNotFoundError(f"Workflow {workflow_id} not found.")
        return self._statuses[workflow_id]
