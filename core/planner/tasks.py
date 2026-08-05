from typing import Any, Dict, List, Optional

from .models import Task
from .enums import TaskState
from .exceptions import TaskError


class TaskManager:
    """Manage task lifecycle and state transitions."""

    def __init__(self):
        self._tasks: Dict[str, Task] = {}

    def create(self, task: Task) -> Task:
        if task.id in self._tasks:
            raise TaskError(f"Task '{task.id}' already exists.")
        self._tasks[task.id] = task
        return task

    def complete(self, task_id: str) -> Task:
        task = self._get(task_id)
        updated = task.with_state(TaskState.SUCCESS)
        self._tasks[task_id] = updated
        return updated

    def fail(self, task_id: str) -> Task:
        task = self._get(task_id)
        updated = task.with_state(TaskState.FAILED)
        self._tasks[task_id] = updated
        return updated

    def skip(self, task_id: str) -> Task:
        task = self._get(task_id)
        updated = task.with_state(TaskState.SKIPPED)
        self._tasks[task_id] = updated
        return updated

    def ready(self, task_id: str) -> Task:
        task = self._get(task_id)
        updated = task.with_state(TaskState.READY)
        self._tasks[task_id] = updated
        return updated

    def pending(self, task_id: str) -> Task:
        task = self._get(task_id)
        updated = task.with_state(TaskState.PENDING)
        self._tasks[task_id] = updated
        return updated

    def get(self, task_id: str) -> Task:
        return self._get(task_id)

    def list(self) -> List[Task]:
        return list(self._tasks.values())

    def _get(self, task_id: str) -> Task:
        if task_id not in self._tasks:
            raise TaskError(f"Task '{task_id}' does not exist.")
        return self._tasks[task_id]
