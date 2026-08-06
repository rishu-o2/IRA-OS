from typing import Any, Mapping

from core.android.models import CapabilityDescriptor, SecurityLevel

from .base import BaseAndroidCapability


class ClipboardCapability(BaseAndroidCapability):
    """
    Capability: android.device.clipboard.read
    Reads the current clipboard text.
    """


    def __init__(self, bridge: SystemBridge):
        self.bridge = bridge

    @property
    def descriptor(self) -> CapabilityDescriptor:
        return CapabilityDescriptor(
            id="android.device.clipboard.read",
            name="Clipboard Read",
            description="Reads the current text from the device clipboard.",
            version="1.0.0",
            security_level=SecurityLevel.LOW,
            supported_actions=("read", "default")
        )

    async def _execute_internal(self, action: str, arguments: Mapping[str, Any]) -> Mapping[str, Any]:
        return await self.bridge.execute('clipboard.read', arguments)
