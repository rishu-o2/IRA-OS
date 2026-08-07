from typing import Any, Mapping, Optional
from core.android.bridge.contracts import NetworkBridge
from core.android.capabilities.base import BaseAndroidCapability
from core.android.models import CapabilityDescriptor, SecurityLevel, CapabilityCategory, ConfirmationLevel

_AIRPLANE_STATUS = "network.airplane.status"
_AIRPLANE_ENABLE = "network.airplane.enable"
_AIRPLANE_DISABLE = "network.airplane.disable"

_MUTATING_ACTIONS = frozenset({
    _AIRPLANE_ENABLE,
    _AIRPLANE_DISABLE,
})

class AirplaneModeCapability(BaseAndroidCapability):
    """
    Capability: android.device.airplane_mode
    Controls Airplane Mode.
    """

    def __init__(self, bridge: NetworkBridge):
        self.bridge = bridge

    @property
    def descriptor(self) -> CapabilityDescriptor:
        return CapabilityDescriptor(
            id="android.device.airplane_mode",
            name="Airplane Mode Control",
            description="Controls device Airplane Mode.",
            version="1.0.0",
            category=CapabilityCategory.NETWORK,
            security_level=SecurityLevel.NORMAL,
            required_permissions=("WRITE_SECURE_SETTINGS",),
            supported_actions=(_AIRPLANE_STATUS, _AIRPLANE_ENABLE, _AIRPLANE_DISABLE),
            conflicts_with=("wifi", "bluetooth", "hotspot", "mobile_data"),
            is_mutation=True,
            supports_rollback=True,
            audit_required=True,
            confirmation_level=ConfirmationLevel.NONE,
            idempotent=False,
        )

    async def _execute_internal(self, action: str, arguments: Mapping[str, Any]) -> Mapping[str, Any]:
        if action in _MUTATING_ACTIONS:
            # Airplane mode enable/disable always returns pre_state from the mock bridge directly
            # because it affects ALL other networking radios.
            res = await self.bridge.execute(action, arguments)
            if isinstance(res, dict) and "pre_state" in res:
                return res
            # Fallback if bridge didn't supply pre_state
            pre_state = await self.bridge.execute(_AIRPLANE_STATUS)
            return {"status": res, "pre_state": {"airplane_mode": pre_state}}
        return await self.bridge.execute(action, arguments)

    def supports_rollback(self, arguments: Mapping[str, Any]) -> bool:
        return arguments.get("action") in _MUTATING_ACTIONS

    async def rollback(self, arguments: Mapping[str, Any], original_result: Any) -> None:
        if original_result and hasattr(original_result, "data") and "pre_state" in original_result.data:
            await self.bridge.execute("network.state.restore", {"state": original_result.data["pre_state"]})
        else:
            action = arguments.get("action")
            if action == _AIRPLANE_ENABLE:
                await self.bridge.execute(_AIRPLANE_DISABLE)
            elif action == _AIRPLANE_DISABLE:
                await self.bridge.execute(_AIRPLANE_ENABLE)
