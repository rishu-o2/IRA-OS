from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

from .models import Goal, Task, ExecutionPlan
from .graph import ExecutionGraph


class PlanningStrategy(ABC):
    """Planning strategy interface."""

    @abstractmethod
    def create_plan(self, goal: Goal, tasks: List[Task]) -> ExecutionPlan:
        ...


class RuleBasedPlanner(PlanningStrategy):
    """Simple deterministic planner that orders tasks by dependencies and priority."""

    def __init__(self, graph_builder: ExecutionGraph):
        self._graph_builder = graph_builder

    def create_plan(self, goal: Goal, tasks: List[Task]) -> ExecutionPlan:
        graph = self._graph_builder.build(tasks)
        sorted_tasks = self._graph_builder.topological_sort(tasks)
        estimated = len(sorted_tasks)
        return ExecutionPlan(goal=goal, tasks=tuple(sorted_tasks), graph=graph, estimated_steps=estimated)
