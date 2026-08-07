from typing import Any, Mapping

from core.android.bridge.contracts import SystemBridge
from core.android.capabilities.base import BaseAndroidCapability
from core.android.models import CapabilityDescriptor, SecurityLevel, ConfirmationLevel


class FlashlightCapability(BaseAndroidCapability):
    """
    Android Flashlight Control capability.
    This is a stateless capability that communicates strictly through SystemBridge.
    """

    def __init__(self, bridge: SystemBridge):
        self._bridge = bridge

    @property
    def descriptor(self) -> CapabilityDescriptor:
        return CapabilityDescriptor(
            id="android.hardware.flashlight",
            name="Flashlight Control",
            description="Controls the device flashlight",
            version="1.0.0",
            security_level=SecurityLevel.LOW,
            supported_actions=(
                "system.flashlight.on",
                "system.flashlight.off",
                "system.flashlight.toggle",
                "system.flashlight.status"
            ),
            is_mutation=True,
            supports_rollback=True,
            audit_required=True,
            confirmation_level=ConfirmationLevel.USER,
            idempotent=False
        )

    async def _execute_internal(self, action: str, arguments: Mapping[str, Any]) -> Mapping[str, Any]:
        """
        Executes the flashlight action via the bridge.
        """
        return await self._bridge.execute(action, arguments)

    def supports_rollback(self, arguments: Mapping[str, Any]) -> bool:
        action = arguments.get("action")
        return action in ("system.flashlight.on", "system.flashlight.off", "system.flashlight.toggle")

    async def rollback(self, arguments: Mapping[str, Any], original_result: Any) -> None:
        action = arguments.get("action")
        if action == "system.flashlight.on":
            await self._bridge.execute("system.flashlight.off")
        elif action == "system.flashlight.off":
            await self._bridge.execute("system.flashlight.on")
        elif action == "system.flashlight.toggle":
            await self._bridge.execute("system.flashlight.toggle")
