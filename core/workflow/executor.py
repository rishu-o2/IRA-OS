from typing import Any

from .contracts import WorkflowExecutor
from .models import WorkflowTask


class DefaultWorkflowExecutor(WorkflowExecutor):
    """
    Scaffold for execution orchestration.
    Dispatches tasks and normalizes results without actual platform execution.
    """

    def __init__(self) -> None:
        pass

    async def dispatch(self, task: WorkflowTask) -> Any:
        # In this scaffold, we simulate a successful dispatch and result collection
        return {"simulated": True, "task_id": task.task_id}
