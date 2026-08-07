from typing import Any, Mapping, Optional

from core.android.bridge.contracts import SystemBridge
from core.android.capabilities.base import BaseAndroidCapability
from core.android.capabilities.exceptions import InvalidArgumentError
from core.android.models import CapabilityDescriptor, ConfirmationLevel, SecurityLevel, CapabilityCategory

_TIMEOUT_GET = "system.screen_timeout.get"
_TIMEOUT_GET_SUPPORTED = "system.screen_timeout.get_supported"
_TIMEOUT_SET = "system.screen_timeout.set"

_MUTATING_ACTIONS = frozenset({_TIMEOUT_SET})


class ScreenTimeoutCapability(BaseAndroidCapability):
    """
    Android Screen Timeout Capability.
    
    Dynamically validates requested timeout values against the bridge's 
    supported values, ensuring platform independence.
    
    Supports precise rollback using pre-state capture.
    """
    
    def __init__(self, bridge: SystemBridge) -> None:
        self._bridge = bridge

    @property
    def descriptor(self) -> CapabilityDescriptor:
        return CapabilityDescriptor(
            id="android.device.screen_timeout",
            name="Screen Timeout Control",
            description="Controls the device screen timeout duration.",
            version="1.0.0",
            category=CapabilityCategory.DISPLAY,
            security_level=SecurityLevel.LOW,
            required_permissions=(),
            supported_actions=(_TIMEOUT_GET, _TIMEOUT_GET_SUPPORTED, _TIMEOUT_SET),
            is_mutation=True,
            supports_rollback=True,
            audit_required=True,
            confirmation_level=ConfirmationLevel.NONE,
            idempotent=False,
        )

    async def _execute_internal(self, action: str, arguments: Mapping[str, Any]) -> Mapping[str, Any]:
        if action in (_TIMEOUT_GET, _TIMEOUT_GET_SUPPORTED):
            return await self._bridge.execute(action, {})
        
        if action == _TIMEOUT_SET:
            duration = arguments.get("duration_ms")
            if duration is None:
                raise InvalidArgumentError("duration_ms is required for set action")
            
            try:
                if isinstance(duration, bool):
                    raise TypeError
                duration_val = int(duration)
            except (ValueError, TypeError):
                raise InvalidArgumentError("duration_ms must be an integer")
                
            # Dynamic validation against bridge-supported values
            supported_response = await self._bridge.execute(_TIMEOUT_GET_SUPPORTED, {})
            supported_values = supported_response.get("supported", [])
            
            if duration_val not in supported_values:
                raise InvalidArgumentError(f"duration_ms {duration_val} is not supported. Supported values: {supported_values}")
                
            return await self._bridge.execute(action, {"duration_ms": duration_val})

        raise InvalidArgumentError(f"Unsupported action: {action}")

    def supports_rollback(self, arguments: Mapping[str, Any]) -> bool:
        return arguments.get("action") in _MUTATING_ACTIONS

    async def rollback(self, arguments: Mapping[str, Any], original_result: Optional[Any] = None) -> None:
        action = arguments.get("action")
        
        if action == _TIMEOUT_SET:
            if hasattr(original_result, "data") and "pre_state" in original_result.data:
                pre_state = original_result.data["pre_state"]
                if "duration_ms" in pre_state:
                    # Bypass validation on rollback since the bridge reported this state previously
                    await self._bridge.execute(_TIMEOUT_SET, {"duration_ms": pre_state["duration_ms"]})
            else:
                # If no pre-state, we can't safely guess a timeout. No-op is the safest fallback.
                pass
