import uuid

from .contracts import WorkflowScheduler
from .models import WorkflowRequest, WorkflowStatus, WorkflowTask


class DefaultWorkflowScheduler(WorkflowScheduler):
    """
    Scaffold implementation of the workflow scheduler.
    Supports parsing schedule constraints without implementing background timers.
    """

    def __init__(self) -> None:
        pass

    def schedule(self, request: WorkflowRequest) -> WorkflowTask:
        task_id = f"task-{uuid.uuid4().hex[:8]}"

        # In a full implementation, the schedule logic would calculate delay/cron
        # and queue the task accordingly. In this scaffold, we simply map it to a task.

        return WorkflowTask(
            task_id=task_id,
            workflow_id=request.workflow_id,
            target_capability=request.target_capability,
            arguments=request.arguments,
            priority=request.priority,
            status=WorkflowStatus.PENDING,
            retry_count=0,
        )
