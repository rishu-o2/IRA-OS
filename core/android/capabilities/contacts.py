"""
Pack C Capability: Contacts

Splits into two capability IDs:
  - android.communication.contacts.read   (read-only, NORMAL security)
  - android.communication.contacts.write  (mutation, NORMAL security, USER confirmation)

Rollback:
  - create -> remove newly created contact
  - update -> restore previous contact fields
  - delete -> restore deleted contact from pre_state
"""
from typing import Any, Mapping

from core.android.bridge.contracts import ContactsBridge
from core.android.capabilities.base import BaseAndroidCapability
from core.android.models import (
    CapabilityCategory, CapabilityDescriptor, ConfirmationLevel, SecurityLevel,
)


# ── Read Capability ────────────────────────────────────────────────────────────

class ContactsReadCapability(BaseAndroidCapability):
    """Read-only contacts capability."""

    def __init__(self, bridge: ContactsBridge) -> None:
        self._bridge = bridge

    @property
    def descriptor(self) -> CapabilityDescriptor:
        return CapabilityDescriptor(
            id="android.communication.contacts.read",
            name="Contacts Read",
            description="Reads and searches the contact book.",
            version="1.0.0",
            category=CapabilityCategory.COMMUNICATION,
            security_level=SecurityLevel.NORMAL,
            supported_actions=("telephony.contacts.read", "telephony.contacts.search"),
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

class ContactsWriteCapability(BaseAndroidCapability):
    """
    Mutation contacts capability.
    All write actions require USER confirmation.
    All write actions are reversible (rollback supported).
    """

    _REVERSIBLE_ACTIONS = frozenset({
        "telephony.contacts.create",
        "telephony.contacts.update",
        "telephony.contacts.delete",
    })

    def __init__(self, bridge: ContactsBridge) -> None:
        self._bridge = bridge

    @property
    def descriptor(self) -> CapabilityDescriptor:
        return CapabilityDescriptor(
            id="android.communication.contacts.write",
            name="Contacts Write",
            description="Creates, updates, or deletes contacts. All actions are reversible.",
            version="1.0.0",
            category=CapabilityCategory.COMMUNICATION,
            security_level=SecurityLevel.NORMAL,
            required_permissions=("READ_CONTACTS", "WRITE_CONTACTS"),
            supported_actions=("telephony.contacts.create", "telephony.contacts.update", "telephony.contacts.delete"),
            is_mutation=True,
            supports_rollback=True,
            audit_required=True,
            confirmation_level=ConfirmationLevel.USER,
            idempotent=False,
        )

    async def _execute_internal(self, action: str, arguments: Mapping[str, Any]) -> Mapping[str, Any]:
        return await self._bridge.execute(action, arguments)

    def supports_rollback(self, arguments: Mapping[str, Any]) -> bool:
        return arguments.get("action") in self._REVERSIBLE_ACTIONS

    async def rollback(self, arguments: Mapping[str, Any], original_result: Any) -> None:
        action = arguments.get("action")

        result_data = original_result
        data = None
        if hasattr(result_data, "data"):
            data = result_data.data
        elif isinstance(result_data, dict):
            data = result_data

        if action == "telephony.contacts.create":
            # Remove the newly created contact
            if data and "contact_id" in data:
                await self._bridge.execute("telephony.contacts.remove", {"contact_id": data["contact_id"]})

        elif action == "telephony.contacts.update":
            # Restore original values from pre_state
            if data and "pre_state" in data:
                pre = data["pre_state"]
                await self._bridge.execute("telephony.contacts.restore", {"contact": pre})

        elif action == "telephony.contacts.delete":
            # Restore the deleted contact from pre_state
            if data and "pre_state" in data:
                await self._bridge.execute("telephony.contacts.restore", {"contact": data["pre_state"]})


# Legacy alias
ContactsCapability = ContactsReadCapability
