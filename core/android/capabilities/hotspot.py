from typing import Any, Mapping, Optional
from core.android.bridge.contracts import NetworkBridge
from core.android.capabilities.base import BaseAndroidCapability
from core.android.models import CapabilityDescriptor, SecurityLevel, CapabilityCategory, ConfirmationLevel

_HOTSPOT_STATUS = "network.hotspot.status"
_HOTSPOT_ENABLE = "network.hotspot.enable"
_HOTSPOT_DISABLE = "network.hotspot.disable"

_MUTATING_ACTIONS = frozenset({
    _HOTSPOT_ENABLE,
    _HOTSPOT_DISABLE,
})

class HotspotCapability(BaseAndroidCapability):
    """
    Capability: android.device.hotspot
    Controls the Hotspot state.
    """

    def __init__(self, bridge: NetworkBridge):
        self.bridge = bridge

    @property
    def descriptor(self) -> CapabilityDescriptor:
        return CapabilityDescriptor(
            id="android.device.hotspot",
            name="Hotspot Control",
            description="Controls device Hotspot state.",
            version="1.0.0",
            category=CapabilityCategory.NETWORK,
            security_level=SecurityLevel.NORMAL,
            required_permissions=("CHANGE_WIFI_STATE",),
            supported_actions=(_HOTSPOT_STATUS, _HOTSPOT_ENABLE, _HOTSPOT_DISABLE),
            conflicts_with=("wifi", "airplane_mode"),
            is_mutation=True,
            supports_rollback=True,
            audit_required=True,
            confirmation_level=ConfirmationLevel.NONE,
            idempotent=False,
        )

    async def _execute_internal(self, action: str, arguments: Mapping[str, Any]) -> Mapping[str, Any]:
        if action in _MUTATING_ACTIONS:
            # Hotspot enable/disable often returns pre_state from the mock bridge directly
            # because it affects other radios like Wi-Fi.
            res = await self.bridge.execute(action, arguments)
            if isinstance(res, dict) and "pre_state" in res:
                return res
            # Fallback if bridge didn't supply pre_state
            pre_state = await self.bridge.execute(_HOTSPOT_STATUS)
            return {"status": res, "pre_state": {"hotspot": pre_state}}
        return await self.bridge.execute(action, arguments)

    def supports_rollback(self, arguments: Mapping[str, Any]) -> bool:
        return arguments.get("action") in _MUTATING_ACTIONS

    async def rollback(self, arguments: Mapping[str, Any], original_result: Any) -> None:
        if original_result and hasattr(original_result, "data") and "pre_state" in original_result.data:
            await self.bridge.execute("network.state.restore", {"state": original_result.data["pre_state"]})
        else:
            action = arguments.get("action")
            if action == _HOTSPOT_ENABLE:
                await self.bridge.execute(_HOTSPOT_DISABLE)
            elif action == _HOTSPOT_DISABLE:
                await self.bridge.execute(_HOTSPOT_ENABLE)
