from typing import Any, Mapping, Optional

from core.android.bridge.contracts import SystemBridge
from core.android.capabilities.base import BaseAndroidCapability
from core.android.capabilities.exceptions import InvalidArgumentError
from core.android.models import CapabilityDescriptor, ConfirmationLevel, SecurityLevel, CapabilityCategory

_ROTATION_GET = "system.rotation.get"
_ROTATION_LOCK = "system.rotation.lock"
_ROTATION_UNLOCK = "system.rotation.unlock"

_MUTATING_ACTIONS = frozenset({_ROTATION_LOCK, _ROTATION_UNLOCK})
_VALID_ORIENTATIONS = frozenset({"PORTRAIT", "LANDSCAPE"})


class RotationCapability(BaseAndroidCapability):
    """
    Android Screen Rotation Capability.
    
    Manages screen rotation lock and orientation.
    Supports precise rollback using pre-state capture.
    """
    
    def __init__(self, bridge: SystemBridge) -> None:
        self._bridge = bridge

    @property
    def descriptor(self) -> CapabilityDescriptor:
        return CapabilityDescriptor(
            id="android.device.rotation",
            name="Rotation Control",
            description="Controls the device screen rotation and orientation lock.",
            version="1.0.0",
            category=CapabilityCategory.DISPLAY,
            security_level=SecurityLevel.LOW,
            required_permissions=(),
            supported_actions=(_ROTATION_GET, _ROTATION_LOCK, _ROTATION_UNLOCK),
            is_mutation=True,
            supports_rollback=True,
            audit_required=True,
            confirmation_level=ConfirmationLevel.NONE,
            idempotent=False,
        )

    async def _execute_internal(self, action: str, arguments: Mapping[str, Any]) -> Mapping[str, Any]:
        if action == _ROTATION_GET:
            return await self._bridge.execute(action, {})
        
        if action == _ROTATION_UNLOCK:
            return await self._bridge.execute(action, {})

        if action == _ROTATION_LOCK:
            orientation = arguments.get("orientation")
            if orientation not in _VALID_ORIENTATIONS:
                raise InvalidArgumentError(f"orientation must be one of: {', '.join(_VALID_ORIENTATIONS)}")
            return await self._bridge.execute(action, {"orientation": orientation})

        raise InvalidArgumentError(f"Unsupported action: {action}")

    def supports_rollback(self, arguments: Mapping[str, Any]) -> bool:
        return arguments.get("action") in _MUTATING_ACTIONS

    async def rollback(self, arguments: Mapping[str, Any], original_result: Optional[Any] = None) -> None:
        action = arguments.get("action")
        
        if hasattr(original_result, "data") and "pre_state" in original_result.data:
            pre_state = original_result.data["pre_state"]
            if pre_state.get("locked"):
                await self._bridge.execute(_ROTATION_LOCK, {"orientation": pre_state.get("orientation", "PORTRAIT")})
            else:
                await self._bridge.execute(_ROTATION_UNLOCK, {})
            return

        # Fallback logical inversion
        if action == _ROTATION_LOCK:
            await self._bridge.execute(_ROTATION_UNLOCK, {})
        elif action == _ROTATION_UNLOCK:
            # We don't know the exact previous lock orientation, default to PORTRAIT lock.
            await self._bridge.execute(_ROTATION_LOCK, {"orientation": "PORTRAIT"})
