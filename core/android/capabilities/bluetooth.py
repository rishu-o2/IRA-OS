from typing import Any, Mapping

from core.android.models import CapabilityDescriptor, SecurityLevel

from .base import BaseAndroidCapability


class BluetoothCapability(BaseAndroidCapability):
    """
    Capability: android.device.bluetooth.state
    Reads the current Bluetooth state.
    """


    def __init__(self, bridge: NetworkBridge):
        self.bridge = bridge

    @property
    def descriptor(self) -> CapabilityDescriptor:
        return CapabilityDescriptor(
            id="android.device.bluetooth.state",
            name="Bluetooth State",
            description="Reads whether Bluetooth is enabled.",
            version="1.0.0",
            security_level=SecurityLevel.LOW,
            required_permissions=("BLUETOOTH",),
            supported_actions=("read", "default")
        )

    async def _execute_internal(self, action: str, arguments: Mapping[str, Any]) -> Mapping[str, Any]:
        return await self.bridge.execute('bluetooth.read', arguments)
