from typing import Any, Mapping
from core.android.bridge.contracts import GalleryBridge
from core.android.capabilities.base import BaseAndroidCapability
from core.android.models import (
    CapabilityCategory, CapabilityDescriptor, ConfirmationLevel, SecurityLevel,
)

class GalleryReadCapability(BaseAndroidCapability):
    def __init__(self, bridge: GalleryBridge) -> None:
        self._bridge = bridge

    @property
    def descriptor(self) -> CapabilityDescriptor:
        return CapabilityDescriptor(
            id="android.device.gallery.read",
            name="Gallery Read",
            description="Reads gallery assets.",
            version="1.0.0",
            category=CapabilityCategory.DEVICE,
            security_level=SecurityLevel.NORMAL,
            supported_actions=("gallery.list",),
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


class GalleryWriteCapability(BaseAndroidCapability):
    def __init__(self, bridge: GalleryBridge) -> None:
        self._bridge = bridge

    @property
    def descriptor(self) -> CapabilityDescriptor:
        return CapabilityDescriptor(
            id="android.device.gallery.write",
            name="Gallery Write",
            description="Adds or deletes gallery assets.",
            version="1.0.0",
            category=CapabilityCategory.DEVICE,
            security_level=SecurityLevel.HIGH,
            supported_actions=("gallery.add", "gallery.delete"),
            is_mutation=True,
            supports_rollback=True,
            audit_required=True,
            confirmation_level=ConfirmationLevel.USER,
            idempotent=False,
        )

    async def _execute_internal(self, action: str, arguments: Mapping[str, Any]) -> Mapping[str, Any]:
        return await self._bridge.execute(action, arguments)

    def supports_rollback(self, arguments: Mapping[str, Any]) -> bool:
        return True

    async def rollback(self, arguments: Mapping[str, Any], original_result: Any) -> None:
        action = arguments.get("action")
        
        result_data = original_result
        data = None
        if hasattr(result_data, "data"):
            data = result_data.data
        elif isinstance(result_data, dict):
            data = result_data

        if not data:
            return

        if action == "gallery.add":
            if "asset_id" in data:
                await self._bridge.execute("gallery.restore_add", {"asset_id": data["asset_id"]})
                
        elif action == "gallery.delete":
            if "asset_id" in data and "pre_state" in data:
                await self._bridge.execute("gallery.restore_delete", {
                    "asset_id": data["asset_id"],
                    "pre_state": data["pre_state"]
                })
