from typing import Any, Mapping
from core.android.bridge.contracts import DownloadBridge
from core.android.capabilities.base import BaseAndroidCapability
from core.android.models import (
    CapabilityCategory, CapabilityDescriptor, ConfirmationLevel, SecurityLevel,
)

class DownloadsReadCapability(BaseAndroidCapability):
    def __init__(self, bridge: DownloadBridge) -> None:
        self._bridge = bridge

    @property
    def descriptor(self) -> CapabilityDescriptor:
        return CapabilityDescriptor(
            id="android.device.downloads.read",
            name="Downloads Read",
            description="Reads download status and queue.",
            version="1.0.0",
            category=CapabilityCategory.DEVICE,
            security_level=SecurityLevel.NORMAL,
            supported_actions=("downloads.list", "downloads.status"),
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


class DownloadsWriteCapability(BaseAndroidCapability):
    _REVERSIBLE = frozenset({"downloads.pause", "downloads.resume"})
    _IRREVERSIBLE = frozenset({"downloads.start", "downloads.cancel", "downloads.delete"})

    def __init__(self, bridge: DownloadBridge) -> None:
        self._bridge = bridge

    @property
    def descriptor(self) -> CapabilityDescriptor:
        return CapabilityDescriptor(
            id="android.device.downloads.write",
            name="Downloads Write",
            description="Manages downloads.",
            version="1.0.0",
            category=CapabilityCategory.DEVICE,
            security_level=SecurityLevel.NORMAL,
            supported_actions=("downloads.start", "downloads.pause", "downloads.resume", "downloads.cancel", "downloads.delete"),
            is_mutation=True,
            supports_rollback=True, # Partial: pause/resume are reversible
            audit_required=True,
            confirmation_level=ConfirmationLevel.USER,
            idempotent=False,
        )

    async def _execute_internal(self, action: str, arguments: Mapping[str, Any]) -> Mapping[str, Any]:
        return await self._bridge.execute(action, arguments)

    def supports_rollback(self, arguments: Mapping[str, Any]) -> bool:
        return arguments.get("action") in self._REVERSIBLE

    async def rollback(self, arguments: Mapping[str, Any], original_result: Any) -> None:
        action = arguments.get("action")
        if action not in self._REVERSIBLE:
            return
            
        result_data = original_result
        data = None
        if hasattr(result_data, "data"):
            data = result_data.data
        elif isinstance(result_data, dict):
            data = result_data

        if not data:
            return

        if action in ("downloads.pause", "downloads.resume"):
            if "download_id" in data and "pre_state" in data:
                await self._bridge.execute("downloads.restore_status", {
                    "download_id": data["download_id"],
                    "pre_state": data["pre_state"]
                })
