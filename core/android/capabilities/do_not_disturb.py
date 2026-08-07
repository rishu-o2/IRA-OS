from typing import Any, Mapping, Optional

from core.android.bridge.contracts import SystemBridge
from core.android.capabilities.base import BaseAndroidCapability
from core.android.capabilities.exceptions import InvalidArgumentError
from core.android.models import CapabilityDescriptor, ConfirmationLevel, SecurityLevel, CapabilityCategory

_DND_GET = "system.dnd.get"
_DND_SET = "system.dnd.set"

_MUTATING_ACTIONS = frozenset({_DND_SET})
_VALID_MODES = frozenset({"NORMAL", "PRIORITY", "ALARMS", "SILENT"})


class DoNotDisturbCapability(BaseAndroidCapability):
    """
    Android Do Not Disturb (DND) Capability.
    
    Manages DND state using OS-agnostic enums (NORMAL, PRIORITY, ALARMS, SILENT).
    The bridge layer is responsible for translating these generic terms into
    platform-specific Android APIs (e.g. NotificationManager.INTERRUPTION_FILTER_PRIORITY).
    
    Supports precise rollback using pre-state capture.
    """
    
    def __init__(self, bridge: SystemBridge) -> None:
        self._bridge = bridge

    @property
    def descriptor(self) -> CapabilityDescriptor:
        return CapabilityDescriptor(
            id="android.device.dnd",
            name="Do Not Disturb Control",
            description="Controls the device Do Not Disturb (DND) mode.",
            version="1.0.0",
            category=CapabilityCategory.AUDIO,
            security_level=SecurityLevel.NORMAL,
            required_permissions=("ACCESS_NOTIFICATION_POLICY",),
            supported_actions=(_DND_GET, _DND_SET),
            is_mutation=True,
            supports_rollback=True,
            audit_required=True,
            confirmation_level=ConfirmationLevel.NONE,
            idempotent=False,
        )

    async def _execute_internal(self, action: str, arguments: Mapping[str, Any]) -> Mapping[str, Any]:
        if action == _DND_GET:
            return await self._bridge.execute(action, {})

        if action == _DND_SET:
            mode = arguments.get("mode")
            if mode not in _VALID_MODES:
                raise InvalidArgumentError(f"mode must be one of: {', '.join(_VALID_MODES)}")
            return await self._bridge.execute(action, {"mode": mode})

        raise InvalidArgumentError(f"Unsupported action: {action}")

    def supports_rollback(self, arguments: Mapping[str, Any]) -> bool:
        return arguments.get("action") in _MUTATING_ACTIONS

    async def rollback(self, arguments: Mapping[str, Any], original_result: Optional[Any] = None) -> None:
        action = arguments.get("action")
        if action == _DND_SET:
            if hasattr(original_result, "data") and "pre_state" in original_result.data:
                pre_state = original_result.data["pre_state"]
                if "mode" in pre_state:
                    await self._bridge.execute(_DND_SET, {"mode": pre_state["mode"]})
                    return
            
            # Fallback if no pre-state was captured (e.g., failure before bridge execution)
            # Default to turning DND back to NORMAL.
            await self._bridge.execute(_DND_SET, {"mode": "NORMAL"})
