from core.container import ContainerProtocol, Lifetime, Module
from core.events import EventBus
from core.logging import LoggerFactory

from .contracts import (
    PluginHealthTracker,
    PluginLoader,
    PluginManager,
    PluginRegistry,
    PluginValidator,
)
from .health import DefaultPluginHealthTracker
from .loader import DefaultPluginLoader
from .manager import PluginManagerImpl
from .registry import InMemoryPluginRegistry
from .validator import DefaultPluginValidator


class PluginModule(Module):
    """DI module for the Plugin Framework subsystem."""

    def configure(self, container: ContainerProtocol) -> None:
        container.register_singleton(PluginHealthTracker, DefaultPluginHealthTracker)
        container.register_singleton(PluginLoader, DefaultPluginLoader)
        container.register_singleton(PluginRegistry, InMemoryPluginRegistry)
        container.register_singleton(PluginValidator, DefaultPluginValidator)

        async def build_manager() -> PluginManager:
            loader = await container.resolve(PluginLoader)
            registry = await container.resolve(PluginRegistry)
            validator = await container.resolve(PluginValidator)
            health = await container.resolve(PluginHealthTracker)
            event_bus = await container.resolve(EventBus)
            logger_factory = await container.resolve(LoggerFactory)
            logger = logger_factory.get("core.plugins")

            return PluginManagerImpl(
                loader=loader,
                registry=registry,
                validator=validator,
                health_tracker=health,
                event_bus=event_bus,
                logger=logger,
            )

        container.register_factory(PluginManager, factory=build_manager, lifetime=Lifetime.SINGLETON)
