from dataclasses import dataclass

from core.events.models import Event


@dataclass(frozen=True, kw_only=True)
class GoalCreated(Event):
    """Published when a new planning goal is created."""
    goal_id: str
    title: str
    priority: int

    @property
    def name(self) -> str:
        return "GoalCreated"


@dataclass(frozen=True, kw_only=True)
class PlanCreated(Event):
    """Published when a plan is successfully created."""
    goal_id: str
    plan_id: str
    estimated_steps: int

    @property
    def name(self) -> str:
        return "PlanCreated"


@dataclass(frozen=True, kw_only=True)
class PlanFailed(Event):
    """Published when plan creation fails."""
    goal_id: str
    error: str

    @property
    def name(self) -> str:
        return "PlanFailed"
