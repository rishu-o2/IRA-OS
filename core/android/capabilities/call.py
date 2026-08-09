"""
Pack C Capability: Phone Calls

Splits into two separate capability IDs:
  - android.communication.phone.read   (read-only, NORMAL security)
  - android.communication.phone.write  (mutation, HIGH security, USER confirmation, irreversible)
"""
from typing import Any, Mapping

from core.android.bridge.contracts import CallBridge
from core.android.capabilities.base import BaseAndroidCapability
from core.android.models import (
    CapabilityCategory, CapabilityDescriptor, ConfirmationLevel, SecurityLevel,
)


# ── Read Capability ────────────────────────────────────────────────────────────

class PhoneReadCapability(BaseAndroidCapability):
    """
    Read-only capability for phone call state.
    Does not enter MutationManager.
    """

    def __init__(self, bridge: CallBridge) -> None:
        self._bridge = bridge

    @property
    def descriptor(self) -> CapabilityDescriptor:
        return CapabilityDescriptor(
            id="android.communication.phone.read",
            name="Phone Status",
            description="Reads current phone call state.",
            version="1.0.0",
            category=CapabilityCategory.COMMUNICATION,
            security_level=SecurityLevel.NORMAL,
            supported_actions=("telephony.phone.status",),
            is_mutation=False,
            supports_rollback=False,
            audit_required=False,
            confirmation_level=ConfirmationLevel.NONE,
            idempotent=True,
        )

    async def _execute_internal(self, action: str, arguments: Mapping[str, Any]) -> Mapping[str, Any]:
        return await self._bridge.execute(action, arguments)

    def supports_rollback(self, arguments: Mapping[str, Any]) -> bool:
        return False


# ── Write Capability ───────────────────────────────────────────────────────────

class PhoneWriteCapability(BaseAndroidCapability):
    """
    Mutation capability for phone call control.
    All actions are HIGH security, USER confirmation, irreversible.
    """

    _WRITE_ACTIONS = frozenset({
        "telephony.phone.call",
        "telephony.phone.end",
        "telephony.phone.reject",
    })

    def __init__(self, bridge: CallBridge) -> None:
        self._bridge = bridge

    @property
    def descriptor(self) -> CapabilityDescriptor:
        return CapabilityDescriptor(
            id="android.communication.phone.write",
            name="Phone Call Control",
            description="Places, ends, or rejects phone calls. All actions are irreversible.",
            version="1.0.0",
            category=CapabilityCategory.COMMUNICATION,
            security_level=SecurityLevel.HIGH,
            required_permissions=("CALL_PHONE", "ANSWER_PHONE_CALLS"),
            supported_actions=tuple(self._WRITE_ACTIONS),
            is_mutation=True,
            supports_rollback=False,   # Call actions are irreversible
            audit_required=True,
            confirmation_level=ConfirmationLevel.USER,
            idempotent=False,
        )

    async def _execute_internal(self, action: str, arguments: Mapping[str, Any]) -> Mapping[str, Any]:
        return await self._bridge.execute(action, arguments)

    def supports_rollback(self, arguments: Mapping[str, Any]) -> bool:
        # Phone actions are irreversible
        return False


# Legacy alias kept for backward compatibility (the old CallCapability stub)
CallCapability = PhoneReadCapability
