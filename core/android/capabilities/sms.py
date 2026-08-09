"""
Pack C Capability: SMS

Splits into two separate capability IDs:
  - android.communication.sms.read    (read-only, NORMAL security)
  - android.communication.sms.write   (mutation, HIGH security, USER confirmation)

Rollback:
  - send   -> irreversible
  - delete -> reversible; restores message from pre_state
"""
from typing import Any, Mapping

from core.android.bridge.contracts import SMSBridge
from core.android.capabilities.base import BaseAndroidCapability
from core.android.models import (
    CapabilityCategory, CapabilityDescriptor, ConfirmationLevel, SecurityLevel,
)


# ── Read Capability ────────────────────────────────────────────────────────────

class SmsReadCapability(BaseAndroidCapability):
    """Read-only SMS capability. Routes through protected read path only."""

    def __init__(self, bridge: SMSBridge) -> None:
        self._bridge = bridge

    @property
    def descriptor(self) -> CapabilityDescriptor:
        return CapabilityDescriptor(
            id="android.communication.sms.read",
            name="SMS Read",
            description="Reads and searches the SMS inbox.",
            version="1.0.0",
            category=CapabilityCategory.COMMUNICATION,
            security_level=SecurityLevel.NORMAL,
            supported_actions=("telephony.sms.read", "telephony.sms.search"),
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

class SmsWriteCapability(BaseAndroidCapability):
    """
    Mutation SMS capability.
    - send   -> HIGH security, USER confirmation, irreversible
    - delete -> HIGH security, USER confirmation, reversible (pre_state captured by bridge)
    """

    def __init__(self, bridge: SMSBridge) -> None:
        self._bridge = bridge

    @property
    def descriptor(self) -> CapabilityDescriptor:
        return CapabilityDescriptor(
            id="android.communication.sms.write",
            name="SMS Write",
            description="Sends or deletes SMS messages. Delete is reversible; send is not.",
            version="1.0.0",
            category=CapabilityCategory.COMMUNICATION,
            security_level=SecurityLevel.HIGH,
            required_permissions=("SEND_SMS", "READ_SMS"),
            supported_actions=("telephony.sms.send", "telephony.sms.delete"),
            is_mutation=True,
            supports_rollback=True,   # delete is reversible
            audit_required=True,
            confirmation_level=ConfirmationLevel.USER,
            idempotent=False,
        )

    async def _execute_internal(self, action: str, arguments: Mapping[str, Any]) -> Mapping[str, Any]:
        return await self._bridge.execute(action, arguments)

    def supports_rollback(self, arguments: Mapping[str, Any]) -> bool:
        # Only delete is reversible; send is not
        return arguments.get("action") == "telephony.sms.delete"

    async def rollback(self, arguments: Mapping[str, Any], original_result: Any) -> None:
        action = arguments.get("action")
        if action == "telephony.sms.delete":
            # Restore the deleted message using pre_state from result
            result_data = original_result
            pre_state = None
            if hasattr(result_data, "data"):
                pre_state = result_data.data.get("pre_state")
            elif isinstance(result_data, dict):
                pre_state = result_data.get("pre_state")
            if pre_state:
                await self._bridge.execute("telephony.sms.restore", {
                    "message_id": pre_state["id"],
                    "message": pre_state,
                })
        # send rollback: no-op, irreversible


# Legacy alias
SmsCapability = SmsReadCapability
