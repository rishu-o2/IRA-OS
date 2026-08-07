from typing import Any, Mapping, Optional
from core.android.bridge.contracts import NetworkBridge
from core.android.capabilities.base import BaseAndroidCapability
from core.android.models import CapabilityDescriptor, SecurityLevel, CapabilityCategory, ConfirmationLevel

_BT_STATUS = "network.bluetooth.status"
_BT_ENABLE = "network.bluetooth.enable"
_BT_DISABLE = "network.bluetooth.disable"
_BT_PAIR = "network.bluetooth.pair"
_BT_UNPAIR = "network.bluetooth.unpair"

_MUTATING_ACTIONS = frozenset({
    _BT_ENABLE,
    _BT_DISABLE,
    _BT_PAIR,
    _BT_UNPAIR,
})

class BluetoothCapability(BaseAndroidCapability):
    """
    Capability: android.device.bluetooth
    Controls the Bluetooth state.
    """

    def __init__(self, bridge: NetworkBridge):
        self.bridge = bridge

    @property
    def descriptor(self) -> CapabilityDescriptor:
        return CapabilityDescriptor(
            id="android.device.bluetooth",
            name="Bluetooth Control",
            description="Controls device Bluetooth state and pairing.",
            version="1.0.0",
            category=CapabilityCategory.NETWORK,
            security_level=SecurityLevel.NORMAL,
            required_permissions=("BLUETOOTH", "BLUETOOTH_ADMIN"),
            supported_actions=(_BT_STATUS, _BT_ENABLE, _BT_DISABLE, _BT_PAIR, _BT_UNPAIR),
            conflicts_with=("airplane_mode",),
            is_mutation=True,
            supports_rollback=True,
            audit_required=True,
            confirmation_level=ConfirmationLevel.NONE,
            idempotent=False,
        )

    async def _execute_internal(self, action: str, arguments: Mapping[str, Any]) -> Mapping[str, Any]:
        if action in _MUTATING_ACTIONS:
            pre_state = await self.bridge.execute(_BT_STATUS)
            res = await self.bridge.execute(action, arguments)
            if isinstance(res, dict) and "pre_state" in res:
                return res
            return {"status": res, "pre_state": {"bluetooth": pre_state}}
        return await self.bridge.execute(action, arguments)

    def supports_rollback(self, arguments: Mapping[str, Any]) -> bool:
        return arguments.get("action") in _MUTATING_ACTIONS

    async def rollback(self, arguments: Mapping[str, Any], original_result: Any) -> None:
        if original_result and hasattr(original_result, "data") and "pre_state" in original_result.data:
            await self.bridge.execute("network.state.restore", {"state": original_result.data["pre_state"]})
        else:
            action = arguments.get("action")
            if action == _BT_ENABLE:
                await self.bridge.execute(_BT_DISABLE)
            elif action == _BT_DISABLE:
                await self.bridge.execute(_BT_ENABLE)
