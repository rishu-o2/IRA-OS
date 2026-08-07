from typing import Any, Mapping, Optional
from core.android.bridge.contracts import NetworkBridge
from core.android.capabilities.base import BaseAndroidCapability
from core.android.models import CapabilityDescriptor, SecurityLevel, CapabilityCategory, ConfirmationLevel

_WIFI_STATUS = "network.wifi.status"
_WIFI_ENABLE = "network.wifi.enable"
_WIFI_DISABLE = "network.wifi.disable"
_WIFI_CONNECT = "network.wifi.connect"
_WIFI_DISCONNECT = "network.wifi.disconnect"

_MUTATING_ACTIONS = frozenset({
    _WIFI_ENABLE,
    _WIFI_DISABLE,
    _WIFI_CONNECT,
    _WIFI_DISCONNECT,
})

class WifiCapability(BaseAndroidCapability):
    """
    Capability: android.device.wifi
    Controls the Wi-Fi state.
    """

    def __init__(self, bridge: NetworkBridge):
        self.bridge = bridge

    @property
    def descriptor(self) -> CapabilityDescriptor:
        return CapabilityDescriptor(
            id="android.device.wifi",
            name="Wi-Fi Control",
            description="Controls device Wi-Fi state and connections.",
            version="1.0.0",
            category=CapabilityCategory.NETWORK,
            security_level=SecurityLevel.NORMAL,
            required_permissions=("ACCESS_WIFI_STATE", "CHANGE_WIFI_STATE"),
            supported_actions=(_WIFI_STATUS, _WIFI_ENABLE, _WIFI_DISABLE, _WIFI_CONNECT, _WIFI_DISCONNECT),
            conflicts_with=("hotspot", "airplane_mode"),
            is_mutation=True,
            supports_rollback=True,
            audit_required=True,
            confirmation_level=ConfirmationLevel.NONE,
            idempotent=False,
        )

    async def _execute_internal(self, action: str, arguments: Mapping[str, Any]) -> Mapping[str, Any]:
        if action in _MUTATING_ACTIONS:
            pre_state = await self.bridge.execute(_WIFI_STATUS)
            res = await self.bridge.execute(action, arguments)
            if isinstance(res, dict) and "pre_state" in res:
                return res
            return {"status": res, "pre_state": {"wifi": pre_state}}
        return await self.bridge.execute(action, arguments)

    def supports_rollback(self, arguments: Mapping[str, Any]) -> bool:
        return arguments.get("action") in _MUTATING_ACTIONS

    async def rollback(self, arguments: Mapping[str, Any], original_result: Any) -> None:
        if original_result and hasattr(original_result, "data") and "pre_state" in original_result.data:
            await self.bridge.execute("network.state.restore", {"state": original_result.data["pre_state"]})
        else:
            action = arguments.get("action")
            if action == _WIFI_ENABLE:
                await self.bridge.execute(_WIFI_DISABLE)
            elif action == _WIFI_DISABLE:
                await self.bridge.execute(_WIFI_ENABLE)
            elif action == _WIFI_CONNECT:
                await self.bridge.execute(_WIFI_DISCONNECT)
