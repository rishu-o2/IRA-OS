from typing import List, Optional

import uuid

from core.events import EventBus
from core.lifecycle.interfaces import LifecycleComponent, HealthCheckable
from core.lifecycle.states import ComponentState
from core.logging import Logger
from core.memory import MemoryManager, MemoryRecord

from .events import GoalCreated, PlanCreated, PlanFailed
from .exceptions import PlannerError
from .goals import GoalManager
from .models import Goal, PlanResult, ExecutionPlan
from .planner import Planner
from .tasks import TaskManager


class PlannerManager(LifecycleComponent, HealthCheckable):
    """Facade tying goals, tasks, planning, memory, events, and logs."""

    def __init__(
        self,
        goal_manager: GoalManager,
        task_manager: TaskManager,
        planner: Planner,
        memory_manager: MemoryManager,
        logger: Logger,
        event_bus: Optional[EventBus] = None,
    ):
        self._goal_manager = goal_manager
        self._task_manager = task_manager
        self._planner = planner
        self._memory_manager = memory_manager
        self._logger = logger
        self._event_bus = event_bus

    async def start(self) -> None:
        self._logger.info("PlannerManager starting.")

    async def shutdown(self) -> None:
        self._logger.info("PlannerManager shutting down.")

    async def health_check(self):
        from core.lifecycle.models import ComponentHealth
        return ComponentHealth(state=ComponentState.RUNNING, details="Planner is available.")

    async def create_goal(self, goal: Goal) -> Goal:
        created = self._goal_manager.create(goal)
        if self._event_bus:
            await self._event_bus.publish(
                GoalCreated(
                    payload={
                        "goal_id": created.id,
                        "title": created.title,
                        "priority": created.priority.value,
                    },
                    source="PlannerManager",
                    goal_id=created.id,
                    title=created.title,
                    priority=created.priority.value,
                )
            )
        return created

    async def build_plan(self, goal_id: str) -> PlanResult:
        try:
            goal = self._goal_manager.get(goal_id)
            tasks = [task for task in self._task_manager.list() if task.goal_id == goal_id]
            plan = self._planner.plan(goal, tasks)
        except PlannerError as exc:
            self._logger.error(f"Planning failed for goal '{goal_id}': {exc}")
            if self._event_bus:
                await self._event_bus.publish(
                    PlanFailed(
                        payload={
                            "goal_id": goal_id,
                            "error": str(exc),
                        },
                        source="PlannerManager",
                        goal_id=goal_id,
                        error=str(exc),
                    )
                )
            return PlanResult(success=False, error=str(exc))

        record = MemoryRecord(
            id=f"planner:{goal_id}:{uuid.uuid4().hex}",
            owner_id=goal_id,
            namespace="planner",
            title=f"Execution plan for goal '{goal.title}'",
            content={
                "goal_id": goal_id,
                "task_ids": [task.id for task in plan.tasks],
                "graph": {task_id: list(deps) for task_id, deps in plan.graph.items()},
                "estimated_steps": plan.estimated_steps,
                "created_at": plan.created_at.isoformat(),
            },
            metadata={
                "goal_state": goal.state.value,
                "priority": goal.priority.value,
            },
            tags=("planner", "goal"),
            importance=goal.priority.value,
        )
        await self._memory_manager.remember(record)

        if self._event_bus:
            await self._event_bus.publish(
                PlanCreated(
                    payload={
                        "goal_id": goal_id,
                        "plan_id": record.id,
                        "estimated_steps": plan.estimated_steps,
                    },
                    source="PlannerManager",
                    goal_id=goal_id,
                    plan_id=record.id,
                    estimated_steps=plan.estimated_steps,
                )
            )

        return PlanResult(success=True, plan=plan)

    def cancel_goal(self, goal_id: str) -> Goal:
        cancelled = self._goal_manager.cancel(goal_id)
        return cancelled

    def status(self, goal_id: str) -> Goal:
        return self._goal_manager.get(goal_id)

    def history(self) -> List[Goal]:
        return self._goal_manager.list()
