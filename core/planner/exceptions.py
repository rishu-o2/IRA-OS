"""Planner subsystem exceptions."""

class PlannerError(Exception):
    """Base exception for planner errors."""


class PlanningError(PlannerError):
    """Raised when a plan cannot be created."""


class GoalError(PlannerError):
    """Raised for goal lifecycle failures."""


class TaskError(PlannerError):
    """Raised for task lifecycle failures."""


class CycleDetectedError(PlannerError):
    """Raised when a task dependency cycle is found."""


class ExecutionGraphError(PlannerError):
    """Raised when the execution graph is invalid."""
