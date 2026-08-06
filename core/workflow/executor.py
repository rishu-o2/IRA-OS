from typing import Any

from core.execution.contracts import ExecutionService
from core.execution.exceptions import ExecutionValidationError
from core.execution.models import ExecutionCommand

from .contracts import WorkflowExecutor
from .exceptions import TaskExecutionError
from .models import WorkflowTask


class DefaultWorkflowExecutor(WorkflowExecutor):
    """
    The real Workflow Executor implementation.

    Dispatches WorkflowTasks through the ExecutionService, which enforces
    the full Security → Runtime pipeline. The Workflow Engine has no
    knowledge of Android, Windows, or any platform. It only knows
    about the ExecutionService contract.
    """

    def __init__(self, execution_service: ExecutionService) -> None:
        self._execution_service = execution_service

    async def dispatch(self, task: WorkflowTask) -> Any:
        """
        Translate a WorkflowTask into an ExecutionCommand and dispatch it
        through the canonical Execution pipeline.
        """
        try:
            command = ExecutionCommand(
                command_id=task.task_id,
                capability_id=task.target_capability,
                arguments=dict(task.arguments),
            )
            outcome = await self._execution_service.execute(command)

            if outcome.denied:
                raise TaskExecutionError(
                    f"Execution denied for capability '{task.target_capability}': "
                    f"{outcome.denial_reason}"
                )
            if outcome.failed:
                raise TaskExecutionError(
                    f"Runtime failure for capability '{task.target_capability}': "
                    f"{outcome.error}"
                )

            return outcome.result_data

        except TaskExecutionError:
            raise
        except ExecutionValidationError as exc:
            raise TaskExecutionError(f"Invalid execution command: {exc}") from exc
        except Exception as exc:
            raise TaskExecutionError(
                f"Unexpected error dispatching task '{task.task_id}': {exc}"
            ) from exc
