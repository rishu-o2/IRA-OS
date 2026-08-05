from collections import defaultdict, deque
from typing import Dict, Iterable, List, Set, Tuple

from .models import Task
from .exceptions import CycleDetectedError, ExecutionGraphError


class ExecutionGraph:
    """Build and validate task dependency graphs."""

    def build(self, tasks: Iterable[Task]) -> Dict[str, Tuple[str, ...]]:
        graph: Dict[str, Tuple[str, ...]] = {}
        task_ids = {task.id for task in tasks}

        for task in tasks:
            for dep in task.dependencies:
                if dep not in task_ids:
                    raise ExecutionGraphError(f"Task '{task.id}' depends on unknown task '{dep}'.")
            graph[task.id] = tuple(task.dependencies)

        self._validate_no_cycle(graph)
        return graph

    def _validate_no_cycle(self, graph: Dict[str, Tuple[str, ...]]) -> None:
        visited: Set[str] = set()
        stack: Set[str] = set()

        def visit(node: str) -> None:
            if node in stack:
                raise CycleDetectedError(f"Cycle detected involving task '{node}'.")
            if node in visited:
                return
            stack.add(node)
            for neighbor in graph.get(node, ()):  # dependencies
                visit(neighbor)
            stack.remove(node)
            visited.add(node)

        for node in graph:
            if node not in visited:
                visit(node)

    def topological_sort(self, tasks: Iterable[Task]) -> List[Task]:
        graph = self.build(tasks)
        in_degree: Dict[str, int] = {task.id: 0 for task in tasks}
        dependents: Dict[str, List[str]] = defaultdict(list)

        task_map = {task.id: task for task in tasks}

        for task_id, deps in graph.items():
            for dep in deps:
                dependents[dep].append(task_id)
                in_degree[task_id] += 1

        # Use priority and id to choose ready tasks deterministically while preserving dependencies.
        ready = [task_id for task_id, degree in in_degree.items() if degree == 0]
        ordered: List[Task] = []

        while ready:
            ready.sort(key=lambda task_id: (-task_map[task_id].priority, task_id))
            current_id = ready.pop(0)
            ordered.append(task_map[current_id])
            for dependent in dependents.get(current_id, []):
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    ready.append(dependent)

        if len(ordered) != len(task_map):
            raise CycleDetectedError("Cycle detected during topological sort.")

        return ordered
