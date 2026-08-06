from core.container import ContainerProtocol, Lifetime, Module
from core.events import EventBus
from core.logging import LoggerFactory
from core.runtime.interfaces import CapabilityRegistry, Dispatcher, Executor
from core.security.contracts import PermissionManager

from .contracts import ExecutionService
from .service import DefaultExecutionService


class ExecutionModule(Module):
    """
    DI module for the Execution Service kernel.

    Registers the ExecutionService as a first-class kernel singleton.
    Depends on: SecurityModule, RuntimeModule (must be installed first).
    """

    def configure(self, container: ContainerProtocol) -> None:

        async def build_execution_service() -> ExecutionService:
            permission_manager = await container.resolve(PermissionManager)
            registry = await container.resolve(CapabilityRegistry)
            dispatcher = await container.resolve(Dispatcher)
            executor = await container.resolve(Executor)
            event_bus = await container.resolve(EventBus)
            logger_factory = await container.resolve(LoggerFactory)
            logger = logger_factory.get("core.execution")

            return DefaultExecutionService(
                permission_manager=permission_manager,
                registry=registry,
                dispatcher=dispatcher,
                executor=executor,
                event_bus=event_bus,
                logger=logger,
            )

        container.register_factory(
            ExecutionService,
            factory=build_execution_service,
            lifetime=Lifetime.SINGLETON,
        )
