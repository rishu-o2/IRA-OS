from core.container import ContainerProtocol, Lifetime, Module
from core.events import EventBus
from core.logging import LoggerFactory
from core.runtime.interfaces import CapabilityRegistry as ToolCapabilityRegistry

from .bridge.contracts import SystemBridge, NetworkBridge, LocationBridge
from .bridge.system import MockSystemBridge
from .bridge.network import MockNetworkBridge
from .bridge.location import MockLocationBridge
from .contracts import AndroidRegistry, AndroidRuntime
from .health import AndroidHealthTracker
from .manager import AndroidRuntimeManager
from .registry import InMemoryAndroidRegistry


class AndroidModule(Module):
    """DI module for the Android Runtime subsystem."""

    def configure(self, container: ContainerProtocol) -> None:
        
        async def build_registry() -> AndroidRegistry:
            event_bus = await container.resolve(EventBus)
            tool_registry = await container.resolve(ToolCapabilityRegistry)
            return InMemoryAndroidRegistry(event_bus, tool_registry)

        async def build_health_tracker() -> AndroidHealthTracker:
            event_bus = await container.resolve(EventBus)
            registry = await container.resolve(AndroidRegistry)
            return AndroidHealthTracker(event_bus, registry)

        async def build_manager() -> AndroidRuntime:
            registry = await container.resolve(AndroidRegistry)
            health_tracker = await container.resolve(AndroidHealthTracker)
            event_bus = await container.resolve(EventBus)
            logger_factory = await container.resolve(LoggerFactory)
            logger = logger_factory.get("core.android")

            return AndroidRuntimeManager(
                registry=registry,
                health_tracker=health_tracker,
                event_bus=event_bus,
                logger=logger,
            )

        container.register_factory(AndroidRegistry, factory=build_registry, lifetime=Lifetime.SINGLETON)
        container.register_factory(AndroidHealthTracker, factory=build_health_tracker, lifetime=Lifetime.SINGLETON)
        container.register_factory(AndroidRuntime, factory=build_manager, lifetime=Lifetime.SINGLETON)

        # Register Bridges
        container.register_singleton(SystemBridge, MockSystemBridge)
        container.register_singleton(NetworkBridge, MockNetworkBridge)
        container.register_singleton(LocationBridge, MockLocationBridge)
