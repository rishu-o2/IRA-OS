from typing import Dict, Tuple
from core.events import EventBus
from core.runtime.interfaces import CapabilityRegistry as ToolCapabilityRegistry

from .contracts import AndroidCapability, AndroidRegistry
from .events import AndroidCapabilityRegistered, AndroidCapabilityRemoved
from .exceptions import AndroidCapabilityRegistrationError
from .adapter import DefaultAndroidAdapter


class InMemoryAndroidRegistry(AndroidRegistry):
    """
    Discovers, registers, and queries Android capabilities.
    Bridges registered capabilities to the Tool Runtime's global registry.
    """

    def __init__(self, event_bus: EventBus, tool_registry: ToolCapabilityRegistry):
        self._event_bus = event_bus
        self._tool_registry = tool_registry
        self._capabilities: Dict[str, AndroidCapability] = {}

    async def register(self, capability: AndroidCapability) -> None:
        descriptor = capability.descriptor
        if not descriptor or not descriptor.id:
            raise AndroidCapabilityRegistrationError("Capability descriptor or ID is invalid.")

        if descriptor.id in self._capabilities:
            raise AndroidCapabilityRegistrationError(f"Capability '{descriptor.id}' already registered.")

        self._capabilities[descriptor.id] = capability

        # Bridge to Tool Runtime
        adapter = DefaultAndroidAdapter(capability)
        await self._tool_registry.register(adapter)

        await self._event_bus.publish(
            AndroidCapabilityRegistered(
                payload={"capability_id": descriptor.id},
                source="AndroidRegistry",
                capability_id=descriptor.id,
                capability_name=descriptor.name,
            )
        )

    async def unregister(self, capability_id: str) -> None:
        if capability_id not in self._capabilities:
            raise AndroidCapabilityRegistrationError(f"Capability '{capability_id}' not found.")

        del self._capabilities[capability_id]
        await self._tool_registry.unregister(capability_id)

        await self._event_bus.publish(
            AndroidCapabilityRemoved(
                payload={"capability_id": capability_id},
                source="AndroidRegistry",
                capability_id=capability_id,
            )
        )

    def lookup(self, capability_id: str) -> AndroidCapability:
        if capability_id not in self._capabilities:
            raise AndroidCapabilityRegistrationError(f"Capability '{capability_id}' not found.")
        return self._capabilities[capability_id]

    def get_all(self) -> Tuple[AndroidCapability, ...]:
        return tuple(self._capabilities.values())
