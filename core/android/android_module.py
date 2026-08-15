from core.container import ContainerProtocol, Lifetime, Module
from core.events import EventBus
from core.logging import LoggerFactory
from core.runtime.interfaces import CapabilityRegistry as ToolCapabilityRegistry

from .bridge.contracts import SystemBridge, NetworkBridge, LocationBridge, CallBridge, SMSBridge, ContactsBridge, NotificationBridge
from .bridge.system import MockSystemBridge
from .bridge.network import MockNetworkBridge
from .bridge.location import MockLocationBridge
from .bridge.telephony import MockCallBridge, MockSMSBridge, MockContactsBridge
from .bridge.notification import MockNotificationBridge
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

            import inspect
            import core.android.capabilities as caps
            capabilities_to_register = []
            for cap_name in caps.__all__:
                cap_cls = getattr(caps, cap_name)
                if not inspect.isabstract(cap_cls):
                    cap_instance = await container.resolve(cap_cls)
                    capabilities_to_register.append(cap_instance)

            return AndroidRuntimeManager(
                registry=registry,
                health_tracker=health_tracker,
                event_bus=event_bus,
                logger=logger,
                capabilities=capabilities_to_register,
            )

        container.register_factory(AndroidRegistry, factory=build_registry, lifetime=Lifetime.SINGLETON)
        container.register_factory(AndroidHealthTracker, factory=build_health_tracker, lifetime=Lifetime.SINGLETON)
        container.register_factory(AndroidRuntime, factory=build_manager, lifetime=Lifetime.SINGLETON)

        container.register_singleton(SystemBridge, MockSystemBridge)
        container.register_singleton(NetworkBridge, MockNetworkBridge)
        container.register_singleton(LocationBridge, MockLocationBridge)

        # Pack C: Communication bridges
        container.register_singleton(CallBridge, MockCallBridge)
        container.register_singleton(SMSBridge, MockSMSBridge)
        container.register_singleton(ContactsBridge, MockContactsBridge)
        container.register_singleton(NotificationBridge, MockNotificationBridge)

        # Pack D: Device & Data Layer bridges
        from .bridge.contracts import (
            CameraBridge, MicrophoneBridge, FileBridge, MediaBridge, 
            GalleryBridge, DownloadBridge, StorageBridge
        )
        from .bridge.camera import MockCameraBridge
        from .bridge.microphone import MockMicrophoneBridge
        from .bridge.files import MockFileBridge
        from .bridge.media import MockMediaBridge
        from .bridge.gallery import MockGalleryBridge
        from .bridge.downloads import MockDownloadBridge
        from .bridge.storage import MockStorageBridge

        container.register_singleton(CameraBridge, MockCameraBridge)
        container.register_singleton(MicrophoneBridge, MockMicrophoneBridge)
        container.register_singleton(FileBridge, MockFileBridge)
        container.register_singleton(MediaBridge, MockMediaBridge)
        container.register_singleton(GalleryBridge, MockGalleryBridge)
        container.register_singleton(DownloadBridge, MockDownloadBridge)
        container.register_singleton(StorageBridge, MockStorageBridge)

        # Auto-register all non-abstract capability classes into the container
        import inspect
        import core.android.capabilities as caps
        for cap_name in caps.__all__:
            cap_cls = getattr(caps, cap_name)
            if not inspect.isabstract(cap_cls):
                container.register_singleton(cap_cls)
