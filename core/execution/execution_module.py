from core.container import ContainerProtocol, Lifetime, Module
from core.events import EventBus
from core.logging import LoggerFactory
from core.runtime.interfaces import CapabilityRegistry, Dispatcher, Executor
from core.security.contracts import PermissionManager

from .contracts import ExecutionService, ExecutionClassifier, ProtectedDispatcher
from .service import DefaultExecutionService, DefaultExecutionClassifier, DefaultProtectedDispatcher


class ExecutionModule(Module):
    """
    DI module for the Execution Service kernel.

    Wires the full hardened execution pipeline:
      ExecutionService
        -> ExecutionClassifier (determines READ vs MUTATION)
        -> ProtectedDispatcher (enforces Security before Runtime dispatch)
        -> MutationManager (injected from MutationModule for mutations)

    Install order: SecurityModule, RuntimeModule, MutationModule, then ExecutionModule.
    """

    def configure(self, container: ContainerProtocol) -> None:

        async def build_classifier() -> ExecutionClassifier:
            registry = await container.resolve(CapabilityRegistry)
            return DefaultExecutionClassifier(registry=registry)

        async def build_protected_dispatcher() -> ProtectedDispatcher:
            permission_manager = await container.resolve(PermissionManager)
            registry = await container.resolve(CapabilityRegistry)
            dispatcher = await container.resolve(Dispatcher)
            executor = await container.resolve(Executor)
            event_bus = await container.resolve(EventBus)
            logger_factory = await container.resolve(LoggerFactory)
            logger = logger_factory.get("core.execution.dispatcher")

            from core.mutation.confirmation import ConfirmationManager
            confirmation_manager = await container.resolve(ConfirmationManager)

            return DefaultProtectedDispatcher(
                permission_manager=permission_manager,
                registry=registry,
                dispatcher=dispatcher,
                executor=executor,
                event_bus=event_bus,
                logger=logger,
                confirmation_manager=confirmation_manager,
            )

        async def build_execution_service() -> ExecutionService:
            from core.mutation.contracts import MutationManager
            classifier = await container.resolve(ExecutionClassifier)
            protected_dispatcher = await container.resolve(ProtectedDispatcher)
            mutation_manager = await container.resolve(MutationManager)
            event_bus = await container.resolve(EventBus)
            logger_factory = await container.resolve(LoggerFactory)
            logger = logger_factory.get("core.execution")

            return DefaultExecutionService(
                classifier=classifier,
                protected_dispatcher=protected_dispatcher,
                mutation_manager=mutation_manager,
                event_bus=event_bus,
                logger=logger,
            )

        container.register_factory(
            ExecutionClassifier,
            factory=build_classifier,
            lifetime=Lifetime.SINGLETON,
        )
        container.register_factory(
            ProtectedDispatcher,
            factory=build_protected_dispatcher,
            lifetime=Lifetime.SINGLETON,
        )
        container.register_factory(
            ExecutionService,
            factory=build_execution_service,
            lifetime=Lifetime.SINGLETON,
        )
