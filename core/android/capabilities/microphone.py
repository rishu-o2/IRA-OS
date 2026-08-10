from typing import Any, Mapping
from core.android.bridge.contracts import MicrophoneBridge
from core.android.capabilities.base import BaseAndroidCapability
from core.android.models import (
    CapabilityCategory, CapabilityDescriptor, ConfirmationLevel, SecurityLevel,
)

class MicrophoneReadCapability(BaseAndroidCapability):
    def __init__(self, bridge: MicrophoneBridge) -> None:
        self._bridge = bridge

    @property
    def descriptor(self) -> CapabilityDescriptor:
        return CapabilityDescriptor(
            id="android.device.microphone.read",
            name="Microphone Read",
            description="Reads microphone state.",
            version="1.0.0",
            category=CapabilityCategory.DEVICE,
            security_level=SecurityLevel.NORMAL,
            supported_actions=("microphone.status",),
            is_mutation=False,
            supports_rollback=False,
            audit_required=False,
            confirmation_level=ConfirmationLevel.NONE,
            idempotent=True,
        )

    async def _execute_internal(self, action: str, arguments: Mapping[str, Any]) -> Mapping[str, Any]:
        return await self._bridge.execute(action, arguments)

    def supports_rollback(self, arguments: Mapping[str, Any]) -> bool:
        return False


class MicrophoneWriteCapability(BaseAndroidCapability):
    def __init__(self, bridge: MicrophoneBridge) -> None:
        self._bridge = bridge

    @property
    def descriptor(self) -> CapabilityDescriptor:
        return CapabilityDescriptor(
            id="android.device.microphone.write",
            name="Microphone Write",
            description="Controls microphone recording.",
            version="1.0.0",
            category=CapabilityCategory.DEVICE,
            security_level=SecurityLevel.HIGH,
            supported_actions=("microphone.record.start", "microphone.record.stop"),
            is_mutation=True,
            supports_rollback=False,
            audit_required=True,
            confirmation_level=ConfirmationLevel.USER,
            idempotent=False,
        )

    async def _execute_internal(self, action: str, arguments: Mapping[str, Any]) -> Mapping[str, Any]:
        return await self._bridge.execute(action, arguments)

    def supports_rollback(self, arguments: Mapping[str, Any]) -> bool:
        return False
