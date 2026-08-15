from typing import Any, Mapping
from core.android.bridge.contracts import FileBridge
from core.android.capabilities.base import BaseAndroidCapability
from core.android.models import (
    CapabilityCategory, CapabilityDescriptor, ConfirmationLevel, SecurityLevel,
)

class FilesReadCapability(BaseAndroidCapability):
    def __init__(self, bridge: FileBridge) -> None:
        self._bridge = bridge

    @property
    def descriptor(self) -> CapabilityDescriptor:
        return CapabilityDescriptor(
            id="android.device.files.read",
            name="Files Read",
            description="Reads and lists files.",
            version="1.0.0",
            category=CapabilityCategory.DEVICE,
            security_level=SecurityLevel.NORMAL,
            supported_actions=("files.read", "files.list"),
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


class FilesWriteCapability(BaseAndroidCapability):
    def __init__(self, bridge: FileBridge) -> None:
        self._bridge = bridge

    @property
    def descriptor(self) -> CapabilityDescriptor:
        return CapabilityDescriptor(
            id="android.device.files.write",
            name="Files Write",
            description="Creates, modifies, and deletes files.",
            version="1.0.0",
            category=CapabilityCategory.DEVICE,
            security_level=SecurityLevel.HIGH,
            supported_actions=("files.create", "files.write", "files.rename", "files.move", "files.delete"),
            is_mutation=True,
            supports_rollback=True,
            audit_required=True,
            confirmation_level=ConfirmationLevel.USER,
            idempotent=False,
        )

    async def _execute_internal(self, action: str, arguments: Mapping[str, Any]) -> Mapping[str, Any]:
        return await self._bridge.execute(action, arguments)

    def supports_rollback(self, arguments: Mapping[str, Any]) -> bool:
        action = arguments.get("action")
        return action in ("files.create", "files.write", "files.rename", "files.move", "files.delete")

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

        if action == "files.create":
            if "path" in data:
                await self._bridge.execute("files.delete", {"path": data["path"]})
                
        elif action == "files.write":
            if "path" in data and "pre_state" in data:
                await self._bridge.execute("files.restore_write", {
                    "path": data["path"],
                    "pre_state": data["pre_state"]
                })
                
        elif action == "files.rename":
            if "pre_state" in data:
                pre = data["pre_state"]
                await self._bridge.execute("files.restore_rename", {
                    "source": pre["source"],
                    "destination": pre["destination"]
                })
                
        elif action == "files.move":
            if "pre_state" in data:
                pre = data["pre_state"]
                await self._bridge.execute("files.restore_move", {
                    "source": pre["source"],
                    "destination": pre["destination"]
                })
                
        elif action == "files.delete":
            if "path" in data and "pre_state" in data:
                await self._bridge.execute("files.restore_delete", {
                    "path": data["path"],
                    "pre_state": data["pre_state"]
                })

class FilesCapability:
    pass

