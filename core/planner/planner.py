from typing import List

from .models import Goal, Task, ExecutionPlan
from .exceptions import PlanningError
from .strategy import PlanningStrategy
from .enums import GoalState


class Planner:
    """Produces a deterministic execution plan from a goal and its tasks."""

    def __init__(self, strategy: PlanningStrategy):
        self._strategy = strategy

    def plan(self, goal: Goal, tasks: List[Task]) -> ExecutionPlan:
        if goal.state == GoalState.CANCELLED:
            raise PlanningError("Cannot plan a cancelled goal.")
        if not tasks:
            raise PlanningError("No tasks provided for planning.")
        return self._strategy.create_plan(goal, tasks)
