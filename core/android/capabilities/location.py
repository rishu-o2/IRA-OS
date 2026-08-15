from typing import Any, Mapping

from core.android.models import CapabilityDescriptor, SecurityLevel, CapabilityCategory
from core.android.bridge.contracts import LocationBridge

from .base import BaseAndroidCapability


class LocationCapability(BaseAndroidCapability):
    """
    Capability: android.device.location.coarse
    Reads the current coarse location.
    """


    def __init__(self, bridge: LocationBridge):
        self.bridge = bridge

    @property
    def descriptor(self) -> CapabilityDescriptor:
        return CapabilityDescriptor(
            id="android.device.location.coarse",
            name="Coarse Location",
            description="Reads the current coarse device location.",
            version="1.0.0",
            category=CapabilityCategory.SENSORS,
            security_level=SecurityLevel.HIGH,
            required_permissions=("ACCESS_COARSE_LOCATION",),
            supported_actions=("read", "default")
        )

    async def _execute_internal(self, action: str, arguments: Mapping[str, Any]) -> Mapping[str, Any]:
        return await self.bridge.execute('location.coarse', arguments)
