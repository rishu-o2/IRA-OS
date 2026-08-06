from core.container import ContainerProtocol, Lifetime, Module
from core.events import EventBus
from core.logging import LoggerFactory

from .dispatcher import RuntimeDispatcher
from .executor import RuntimeExecutor
from .interfaces import CapabilityRegistry, Dispatcher, Executor, Validator
from .manager import RuntimeManager
from .registry import InMemoryCapabilityRegistry
from .validator import RuntimeValidator


class RuntimeModule(Module):
    """DI module for the Tool Runtime subsystem."""

    def configure(self, container: ContainerProtocol) -> None:
        container.register_singleton(Validator, RuntimeValidator)
        container.register_singleton(Dispatcher, RuntimeDispatcher)
        container.register_singleton(Executor, RuntimeExecutor)

        async def build_registry() -> CapabilityRegistry:
            event_bus = await container.resolve(EventBus)
            return InMemoryCapabilityRegistry(event_bus)

        async def build_manager() -> RuntimeManager:
            validator = await container.resolve(Validator)
            registry = await container.resolve(CapabilityRegistry)
            dispatcher = await container.resolve(Dispatcher)
            executor = await container.resolve(Executor)
            event_bus = await container.resolve(EventBus)
            logger_factory = await container.resolve(LoggerFactory)
            logger = logger_factory.get("core.runtime")

            return RuntimeManager(
                validator=validator,
                registry=registry,
                dispatcher=dispatcher,
                executor=executor,
                event_bus=event_bus,
                logger=logger,
            )

        container.register_factory(CapabilityRegistry, factory=build_registry, lifetime=Lifetime.SINGLETON)
        container.register_factory(RuntimeManager, factory=build_manager, lifetime=Lifetime.SINGLETON)
