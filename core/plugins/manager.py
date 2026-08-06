from typing import List

from core.events import EventBus
from core.lifecycle.interfaces import LifecycleComponent
from core.lifecycle.models import ComponentHealth
from core.logging import Logger

from .contracts import (
    PluginHealthTracker,
    PluginLoader,
    PluginManager,
    PluginRegistry,
    PluginValidator,
)
from .events import (
    PluginDisabled,
    PluginDiscovered,
    PluginEnabled,
    PluginLoaded,
    PluginRegistered,
    PluginRemoved,
    PluginUnloaded,
    PluginValidationFailed,
)
from .exceptions import PluginNotFoundError, PluginStateError, PluginValidationError
from .models import (
    PluginDescriptor,
    PluginRequest,
    PluginResult,
    PluginState,
    PluginStatus,
)


class PluginManagerImpl(PluginManager, LifecycleComponent):
    """
    Orchestrates the canonical Plugin pipeline.
    """

    def __init__(
        self,
        loader: PluginLoader,
        registry: PluginRegistry,
        validator: PluginValidator,
        health_tracker: PluginHealthTracker,
        event_bus: EventBus,
        logger: Logger,
    ):
        self._loader = loader
        self._registry = registry
        self._validator = validator
        self._health_tracker = health_tracker
        self._event_bus = event_bus
        self._logger = logger

    async def start(self) -> None:
        self._health_tracker.set_available(True)
        self._logger.info("PluginManager started.")

    async def shutdown(self) -> None:
        self._health_tracker.set_available(False)
        self._logger.info("PluginManager shut down.")

    async def health_check(self) -> ComponentHealth:
        return self._health_tracker.check_health()

    async def discover(self) -> None:
        metadatas = self._loader.discover()
        
        for metadata in metadatas:
            plugin_id = metadata.manifest.id
            try:
                self._validator.validate(metadata)
                
                descriptor = PluginDescriptor(
                    plugin_id=plugin_id,
                    metadata=metadata,
                    state=PluginState.DISCOVERED,
                    status=PluginStatus.HEALTHY,
                )
                self._registry.register(descriptor)
                
                await self._event_bus.publish(
                    PluginDiscovered(
                        payload={"plugin_id": plugin_id},
                        plugin_id=plugin_id,
                        metadata={"name": metadata.manifest.name, "version": metadata.manifest.version},
                        source="PluginManager"
                    )
                )
                
            except PluginValidationError as e:
                self._logger.error(f"Plugin validation failed for {plugin_id}: {e}")
                await self._event_bus.publish(
                    PluginValidationFailed(
                        payload={"plugin_id": plugin_id, "error": str(e)},
                        plugin_id=plugin_id,
                        error=str(e),
                        source="PluginManager"
                    )
                )

    async def load(self, request: PluginRequest) -> PluginResult:
        descriptor = self._registry.lookup(request.plugin_id)
        if not descriptor:
            raise PluginNotFoundError(f"Plugin {request.plugin_id} not found in registry.")

        if descriptor.state != PluginState.DISCOVERED:
            raise PluginStateError(f"Cannot load plugin in state {descriptor.state}")

        # Update registry state (immutable dataclass means replacing it)
        new_desc = PluginDescriptor(
            plugin_id=descriptor.plugin_id,
            metadata=descriptor.metadata,
            state=PluginState.LOADED,
            status=descriptor.status
        )
        self._registry.register(new_desc)
        
        await self._event_bus.publish(
            PluginLoaded(payload={"plugin_id": descriptor.plugin_id}, plugin_id=descriptor.plugin_id, source="PluginManager")
        )

        return PluginResult(plugin_id=descriptor.plugin_id, success=True, state=PluginState.LOADED)

    async def unload(self, plugin_id: str) -> PluginResult:
        descriptor = self._registry.lookup(plugin_id)
        if not descriptor:
            raise PluginNotFoundError(f"Plugin {plugin_id} not found in registry.")

        if descriptor.state == PluginState.ENABLED:
            await self.disable(plugin_id)

        new_desc = PluginDescriptor(
            plugin_id=descriptor.plugin_id,
            metadata=descriptor.metadata,
            state=PluginState.DISCOVERED,  # Returning to discovered state
            status=descriptor.status
        )
        self._registry.register(new_desc)
        
        await self._event_bus.publish(
            PluginUnloaded(payload={"plugin_id": plugin_id}, plugin_id=plugin_id, source="PluginManager")
        )

        return PluginResult(plugin_id=plugin_id, success=True, state=PluginState.DISCOVERED)

    async def enable(self, plugin_id: str) -> PluginResult:
        descriptor = self._registry.lookup(plugin_id)
        if not descriptor:
            raise PluginNotFoundError(f"Plugin {plugin_id} not found in registry.")

        if descriptor.state != PluginState.LOADED:
            raise PluginStateError(f"Plugin must be LOADED to enable, currently {descriptor.state}")

        new_desc = PluginDescriptor(
            plugin_id=descriptor.plugin_id,
            metadata=descriptor.metadata,
            state=PluginState.ENABLED,
            status=descriptor.status
        )
        self._registry.register(new_desc)
        
        await self._event_bus.publish(
            PluginEnabled(payload={"plugin_id": plugin_id}, plugin_id=plugin_id, source="PluginManager")
        )

        return PluginResult(plugin_id=plugin_id, success=True, state=PluginState.ENABLED)

    async def disable(self, plugin_id: str) -> PluginResult:
        descriptor = self._registry.lookup(plugin_id)
        if not descriptor:
            raise PluginNotFoundError(f"Plugin {plugin_id} not found in registry.")

        if descriptor.state != PluginState.ENABLED:
            raise PluginStateError(f"Plugin must be ENABLED to disable, currently {descriptor.state}")

        new_desc = PluginDescriptor(
            plugin_id=descriptor.plugin_id,
            metadata=descriptor.metadata,
            state=PluginState.LOADED, # Returns to loaded state
            status=descriptor.status
        )
        self._registry.register(new_desc)
        
        await self._event_bus.publish(
            PluginDisabled(payload={"plugin_id": plugin_id}, plugin_id=plugin_id, source="PluginManager")
        )

        return PluginResult(plugin_id=plugin_id, success=True, state=PluginState.LOADED)

    async def status(self, plugin_id: str) -> PluginStatus:
        descriptor = self._registry.lookup(plugin_id)
        if not descriptor:
            raise PluginNotFoundError(f"Plugin {plugin_id} not found.")
        return descriptor.status

    async def plugins(self) -> List[PluginDescriptor]:
        return self._registry.enumerate()
