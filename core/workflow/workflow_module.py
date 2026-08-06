from core.container import ContainerProtocol, Lifetime, Module
from core.events import EventBus
from core.logging import LoggerFactory

from .contracts import WorkflowExecutor, WorkflowManager, WorkflowQueue, WorkflowScheduler
from .executor import DefaultWorkflowExecutor
from .manager import WorkflowManagerImpl
from .queue import InMemoryWorkflowQueue
from .scheduler import DefaultWorkflowScheduler


class WorkflowModule(Module):
    """DI module for the Task & Workflow Engine subsystem."""

    def configure(self, container: ContainerProtocol) -> None:
        container.register_singleton(WorkflowScheduler, DefaultWorkflowScheduler)
        container.register_singleton(WorkflowQueue, InMemoryWorkflowQueue)
        container.register_singleton(WorkflowExecutor, DefaultWorkflowExecutor)

        async def build_manager() -> WorkflowManager:
            scheduler = await container.resolve(WorkflowScheduler)
            queue = await container.resolve(WorkflowQueue)
            executor = await container.resolve(WorkflowExecutor)
            event_bus = await container.resolve(EventBus)
            logger_factory = await container.resolve(LoggerFactory)
            logger = logger_factory.get("core.workflow")

            return WorkflowManagerImpl(
                scheduler=scheduler,
                queue=queue,
                executor=executor,
                event_bus=event_bus,
                logger=logger,
            )

        container.register_factory(WorkflowManager, factory=build_manager, lifetime=Lifetime.SINGLETON)
