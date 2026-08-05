from core.container import Lifetime, Module, ContainerProtocol
from core.events import EventBus
from core.logging import LoggerFactory, Logger
from core.memory import MemoryManager

from .goals import GoalManager
from .tasks import TaskManager
from .planner import Planner
from .strategy import RuleBasedPlanner
from .graph import ExecutionGraph
from .manager import PlannerManager


class PlannerModule(Module):
    """DI module for the Planner subsystem."""

    def configure(self, container: ContainerProtocol) -> None:
        container.register_singleton(GoalManager)
        container.register_singleton(TaskManager)
        container.register_singleton(ExecutionGraph)
        container.register_singleton(RuleBasedPlanner)

        async def build_planner() -> Planner:
            graph = await container.resolve(ExecutionGraph)
            strategy = await container.resolve(RuleBasedPlanner)
            return Planner(strategy)

        async def build_planner_manager() -> PlannerManager:
            goal_manager = await container.resolve(GoalManager)
            task_manager = await container.resolve(TaskManager)
            planner = await container.resolve(Planner)
            memory_manager = await container.resolve(MemoryManager)
            logger_factory = await container.resolve(LoggerFactory)
            logger = logger_factory.get("core.planner")

            event_bus = None
            if container.has(EventBus):
                event_bus = await container.resolve(EventBus)

            return PlannerManager(goal_manager, task_manager, planner, memory_manager, logger, event_bus)

        container.register_factory(Planner, factory=build_planner, lifetime=Lifetime.SINGLETON)
        container.register_factory(PlannerManager, factory=build_planner_manager, lifetime=Lifetime.SINGLETON)
