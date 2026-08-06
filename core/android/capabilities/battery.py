from typing import Any, Mapping

from core.android.bridge.contracts import SystemBridge
from core.android.models import CapabilityDescriptor, SecurityLevel

from .base import BaseAndroidCapability


class BatteryCapability(BaseAndroidCapability):
    """
    Capability: android.device.battery
    Reads the current battery level and charging state.
    """


    def __init__(self, bridge: SystemBridge):
        self.bridge = bridge

    @property
    def descriptor(self) -> CapabilityDescriptor:
        return CapabilityDescriptor(
            id="android.device.battery",
            name="Battery Status",
            description="Reads device battery level and charging status.",
            version="1.0.0",
            security_level=SecurityLevel.LOW,
            supported_actions=("read", "default")
        )

    async def _execute_internal(self, action: str, arguments: Mapping[str, Any]) -> Mapping[str, Any]:
        return await self.bridge.execute('battery.read', arguments)
