from typing import Dict, List, Optional

from .contracts import WorkflowQueue
from .models import WorkflowTask


class InMemoryWorkflowQueue(WorkflowQueue):
    """
    In-memory task queue management scaffold.
    No threading, no background workers.
    """

    def __init__(self) -> None:
        self._queue: List[WorkflowTask] = []
        self._lookup: Dict[str, WorkflowTask] = {}

    def enqueue(self, task: WorkflowTask) -> None:
        self._queue.append(task)
        self._lookup[task.task_id] = task

    def dequeue(self) -> Optional[WorkflowTask]:
        if not self._queue:
            return None
        task = self._queue.pop(0)
        self._lookup.pop(task.task_id, None)
        return task

    def peek(self) -> Optional[WorkflowTask]:
        if not self._queue:
            return None
        return self._queue[0]

    def remove(self, task_id: str) -> bool:
        task = self._lookup.pop(task_id, None)
        if task:
            self._queue = [t for t in self._queue if t.task_id != task_id]
            return True
        return False

    def lookup(self, task_id: str) -> Optional[WorkflowTask]:
        return self._lookup.get(task_id)

    def status(self) -> dict:
        return {
            "queued_tasks": len(self._queue),
            "tracked_tasks": len(self._lookup),
        }
