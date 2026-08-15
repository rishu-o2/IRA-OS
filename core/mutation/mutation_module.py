from core.container import ContainerProtocol, Lifetime, Module
from core.events import EventBus
from core.logging import LoggerFactory
from core.runtime.interfaces import CapabilityRegistry

from .audit import AuditManager, InMemoryAuditSink
from .confirmation import ConfirmationManager
from .contracts import ConfirmationProvider, MutationManager
from .manager import DefaultMutationManager
from .providers import DenyByDefaultProvider


class MutationModule(Module):
    """
    DI module for the Mutation Lifecycle Framework subsystem.

    Registers MutationManager as a kernel singleton owned by ExecutionService.
    MutationManager does NOT depend on ExecutionService. It receives a
    ProtectedDispatcher at call time from DefaultExecutionService.

    Depends on: RuntimeModule (must be installed first for CapabilityRegistry).
    """

    def configure(self, container: ContainerProtocol) -> None:

        async def build_audit_manager() -> AuditManager:
            logger_factory = await container.resolve(LoggerFactory)
            logger = logger_factory.get("core.mutation.audit")
            manager = AuditManager(logger)
            manager.register_sink(InMemoryAuditSink())
            return manager

        async def build_confirmation_manager() -> ConfirmationManager:
            logger_factory = await container.resolve(LoggerFactory)
            logger = logger_factory.get("core.mutation.confirmation")
            manager = ConfirmationManager(logger)
            manager.register_provider(DenyByDefaultProvider())
            return manager

        async def build_mutation_manager() -> MutationManager:
            registry = await container.resolve(CapabilityRegistry)
            confirmation_manager = await container.resolve(ConfirmationManager)
            audit_manager = await container.resolve(AuditManager)
            event_bus = await container.resolve(EventBus)
            logger_factory = await container.resolve(LoggerFactory)
            logger = logger_factory.get("core.mutation")

            return DefaultMutationManager(
                capability_registry=registry,
                confirmation_manager=confirmation_manager,
                audit_manager=audit_manager,
                event_bus=event_bus,
                logger=logger,
            )

        container.register_factory(
            AuditManager,
            factory=build_audit_manager,
            lifetime=Lifetime.SINGLETON,
        )
        container.register_factory(
            ConfirmationManager,
            factory=build_confirmation_manager,
            lifetime=Lifetime.SINGLETON,
        )
        container.register_factory(
            MutationManager,
            factory=build_mutation_manager,
            lifetime=Lifetime.SINGLETON,
        )
