from typing import Dict, Tuple

from core.events import EventBus
from core.lifecycle.interfaces import HealthCheckable
from core.lifecycle.models import ComponentHealth
from core.lifecycle.states import ComponentState

from .events import CapabilityRegistered, CapabilityUnregistered
from .exceptions import CapabilityNotFoundError, ValidationError
from .interfaces import Capability, CapabilityRegistry


class InMemoryCapabilityRegistry(CapabilityRegistry, HealthCheckable):
    """In-memory registry for capabilities."""

    def __init__(self, event_bus: EventBus):
        self._capabilities: Dict[str, Capability] = {}
        self._event_bus = event_bus

    async def health_check(self) -> ComponentHealth:
        return ComponentHealth(state=ComponentState.RUNNING, details=f"Registry available with {len(self._capabilities)} capabilities.")

    async def register(self, capability: Capability) -> None:
        if not capability:
            raise ValidationError("Capability cannot be None.")
        metadata = capability.metadata
        if not metadata or not metadata.id:
            raise ValidationError("Capability must have valid metadata and ID.")

        if metadata.id in self._capabilities:
            raise ValidationError(f"Capability with ID '{metadata.id}' is already registered.")

        self._capabilities[metadata.id] = capability

        await self._event_bus.publish(
            CapabilityRegistered(
                payload={"capability_id": metadata.id},
                source="CapabilityRegistry",
                capability_id=metadata.id,
                capability_name=metadata.name,
            )
        )

    async def unregister(self, capability_id: str) -> None:
        if capability_id not in self._capabilities:
            raise CapabilityNotFoundError(f"Capability '{capability_id}' not found.")
        del self._capabilities[capability_id]

        await self._event_bus.publish(
            CapabilityUnregistered(
                payload={"capability_id": capability_id},
                source="CapabilityRegistry",
                capability_id=capability_id,
            )
        )

    def lookup(self, capability_id: str) -> Capability:
        if capability_id not in self._capabilities:
            raise CapabilityNotFoundError(f"Capability '{capability_id}' not found.")
        return self._capabilities[capability_id]

    def get_all(self) -> Tuple[Capability, ...]:
        return tuple(self._capabilities.values())
