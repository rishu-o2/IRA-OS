from typing import Any, Mapping, Optional

from core.android.bridge.contracts import SystemBridge
from core.android.capabilities.base import BaseAndroidCapability
from core.android.capabilities.exceptions import InvalidArgumentError
from core.android.models import CapabilityDescriptor, ConfirmationLevel, SecurityLevel, CapabilityCategory

_VIBRATE_START = "system.vibrate.start"
_VIBRATE_CANCEL = "system.vibrate.cancel"

_MUTATING_ACTIONS = frozenset({_VIBRATE_START, _VIBRATE_CANCEL})

class VibrateCapability(BaseAndroidCapability):
    """
    Android Device Vibration Capability.
    
    This is an Ephemeral Mutation capability. It triggers a physical action 
    (vibration) that terminates automatically, meaning there is no persistent
    state to capture or restore perfectly.
    
    Rollback uses logical inversion: start -> cancel.
    """
    
    def __init__(self, bridge: SystemBridge) -> None:
        self._bridge = bridge

    @property
    def descriptor(self) -> CapabilityDescriptor:
        return CapabilityDescriptor(
            id="android.device.vibrate",
            name="Vibrate Control",
            description="Controls device vibration motor. Triggers ephemeral actions.",
            version="1.0.0",
            category=CapabilityCategory.DEVICE,
            security_level=SecurityLevel.LOW,
            required_permissions=("VIBRATE",),
            supported_actions=tuple(_MUTATING_ACTIONS),
            is_mutation=True,
            supports_rollback=True,
            audit_required=True,
            confirmation_level=ConfirmationLevel.NONE,
            idempotent=False,
        )

    async def _execute_internal(self, action: str, arguments: Mapping[str, Any]) -> Mapping[str, Any]:
        if action not in _MUTATING_ACTIONS:
            raise InvalidArgumentError(f"Unsupported action: {action}")

        if action == _VIBRATE_START:
            duration = arguments.get("duration_ms")
            if duration is None:
                raise InvalidArgumentError("duration_ms is required for start action")
            try:
                # Disallow bools passing as ints
                if isinstance(duration, bool):
                    raise TypeError
                duration_val = int(duration)
                if duration_val <= 0:
                    raise ValueError
            except (ValueError, TypeError):
                raise InvalidArgumentError("duration_ms must be a positive integer")
            
            return await self._bridge.execute(action, {"duration_ms": duration_val})

        return await self._bridge.execute(action, {})

    def supports_rollback(self, arguments: Mapping[str, Any]) -> bool:
        return arguments.get("action") in _MUTATING_ACTIONS

    async def rollback(self, arguments: Mapping[str, Any], original_result: Optional[Any] = None) -> None:
        action = arguments.get("action")
        if action == _VIBRATE_START:
            await self._bridge.execute(_VIBRATE_CANCEL, {})
        # If action was cancel, it is ephemeral. We cannot reconstruct a past vibration safely. No-op.
