from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .models import Goal
from .enums import GoalState
from .exceptions import GoalError


class GoalManager:
    """Manage goal lifecycle and state transitions."""

    def __init__(self):
        self._goals: Dict[str, Goal] = {}

    def create(self, goal: Goal) -> Goal:
        if goal.id in self._goals:
            raise GoalError(f"Goal '{goal.id}' already exists.")
        self._goals[goal.id] = goal
        return goal

    def update(self, goal_id: str, **fields: Any) -> Goal:
        if goal_id not in self._goals:
            raise GoalError(f"Goal '{goal_id}' does not exist.")
        current = self._goals[goal_id]
        updated = current.with_update(**fields)
        self._goals[goal_id] = updated
        return updated

    def cancel(self, goal_id: str) -> Goal:
        if goal_id not in self._goals:
            raise GoalError(f"Goal '{goal_id}' does not exist.")
        current = self._goals[goal_id]
        cancelled = current.with_state(GoalState.CANCELLED)
        self._goals[goal_id] = cancelled
        return cancelled

    def get(self, goal_id: str) -> Goal:
        if goal_id not in self._goals:
            raise GoalError(f"Goal '{goal_id}' does not exist.")
        return self._goals[goal_id]

    def list(self, state: Optional[str] = None) -> List[Goal]:
        goals = list(self._goals.values())
        if state is not None:
            goals = [goal for goal in goals if goal.state == state]
        return goals
