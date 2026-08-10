from typing import Any, Mapping
from core.android.bridge.contracts import MediaBridge
from core.android.capabilities.base import BaseAndroidCapability
from core.android.models import (
    CapabilityCategory, CapabilityDescriptor, ConfirmationLevel, SecurityLevel,
)

class MediaReadCapability(BaseAndroidCapability):
    def __init__(self, bridge: MediaBridge) -> None:
        self._bridge = bridge

    @property
    def descriptor(self) -> CapabilityDescriptor:
        return CapabilityDescriptor(
            id="android.device.media.read",
            name="Media Read",
            description="Reads media playback state.",
            version="1.0.0",
            category=CapabilityCategory.DEVICE,
            security_level=SecurityLevel.NORMAL,
            supported_actions=("media.status",),
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


class MediaWriteCapability(BaseAndroidCapability):
    def __init__(self, bridge: MediaBridge) -> None:
        self._bridge = bridge

    @property
    def descriptor(self) -> CapabilityDescriptor:
        return CapabilityDescriptor(
            id="android.device.media.write",
            name="Media Write",
            description="Controls media playback.",
            version="1.0.0",
            category=CapabilityCategory.DEVICE,
            security_level=SecurityLevel.NORMAL,
            supported_actions=("media.play", "media.pause", "media.stop"),
            is_mutation=True,
            supports_rollback=False,
            audit_required=True,
            confirmation_level=ConfirmationLevel.NONE,
            idempotent=False,
        )

    async def _execute_internal(self, action: str, arguments: Mapping[str, Any]) -> Mapping[str, Any]:
        return await self._bridge.execute(action, arguments)

    def supports_rollback(self, arguments: Mapping[str, Any]) -> bool:
        return False

class MediaCapability:
    pass

