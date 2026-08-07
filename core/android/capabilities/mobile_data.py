from typing import Any, Mapping, Optional
from core.android.bridge.contracts import NetworkBridge
from core.android.capabilities.base import BaseAndroidCapability
from core.android.models import CapabilityDescriptor, SecurityLevel, CapabilityCategory, ConfirmationLevel

_MD_STATUS = "network.mobile_data.status"
_MD_ENABLE = "network.mobile_data.enable"
_MD_DISABLE = "network.mobile_data.disable"

_MUTATING_ACTIONS = frozenset({
    _MD_ENABLE,
    _MD_DISABLE,
})

class MobileDataCapability(BaseAndroidCapability):
    """
    Capability: android.device.mobile_data
    Controls the Mobile Data state.
    """

    def __init__(self, bridge: NetworkBridge):
        self.bridge = bridge

    @property
    def descriptor(self) -> CapabilityDescriptor:
        return CapabilityDescriptor(
            id="android.device.mobile_data",
            name="Mobile Data Control",
            description="Controls device Mobile Data state.",
            version="1.0.0",
            category=CapabilityCategory.NETWORK,
            security_level=SecurityLevel.NORMAL,
            required_permissions=("MODIFY_PHONE_STATE",),
            supported_actions=(_MD_STATUS, _MD_ENABLE, _MD_DISABLE),
            conflicts_with=("airplane_mode",),
            is_mutation=True,
            supports_rollback=True,
            audit_required=True,
            confirmation_level=ConfirmationLevel.NONE,
            idempotent=False,
        )

    async def _execute_internal(self, action: str, arguments: Mapping[str, Any]) -> Mapping[str, Any]:
        if action in _MUTATING_ACTIONS:
            pre_state = await self.bridge.execute(_MD_STATUS)
            res = await self.bridge.execute(action, arguments)
            if isinstance(res, dict) and "pre_state" in res:
                return res
            return {"status": res, "pre_state": {"mobile_data": pre_state}}
        return await self.bridge.execute(action, arguments)

    def supports_rollback(self, arguments: Mapping[str, Any]) -> bool:
        return arguments.get("action") in _MUTATING_ACTIONS

    async def rollback(self, arguments: Mapping[str, Any], original_result: Any) -> None:
        if original_result and hasattr(original_result, "data") and "pre_state" in original_result.data:
            await self.bridge.execute("network.state.restore", {"state": original_result.data["pre_state"]})
        else:
            action = arguments.get("action")
            if action == _MD_ENABLE:
                await self.bridge.execute(_MD_DISABLE)
            elif action == _MD_DISABLE:
                await self.bridge.execute(_MD_ENABLE)
