from typing import Any, Mapping

from core.android.models import CapabilityDescriptor, SecurityLevel

from .base import BaseAndroidCapability


class WifiCapability(BaseAndroidCapability):
    """
    Capability: android.device.wifi.state
    Reads the current Wi-Fi state.
    """


    def __init__(self, bridge: NetworkBridge):
        self.bridge = bridge

    @property
    def descriptor(self) -> CapabilityDescriptor:
        return CapabilityDescriptor(
            id="android.device.wifi.state",
            name="Wi-Fi State",
            description="Reads whether Wi-Fi is enabled and connected.",
            version="1.0.0",
            security_level=SecurityLevel.LOW,
            required_permissions=("ACCESS_WIFI_STATE", "ACCESS_NETWORK_STATE"),
            supported_actions=("read", "default")
        )

    async def _execute_internal(self, action: str, arguments: Mapping[str, Any]) -> Mapping[str, Any]:
        return await self.bridge.execute('wifi.read', arguments)
