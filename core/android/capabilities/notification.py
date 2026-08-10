"""
Pack C Capability: Notifications

Splits into three capability IDs:
  - android.communication.notification.read   (read-only, NORMAL security)
  - android.communication.notification.write  (mutation, NORMAL security, NONE confirmation)
      -> dismiss: reversible
      -> clear:   reversible
  - android.communication.notification.reply  (mutation, HIGH security, USER confirmation)
      -> reply: irreversible

Rollback:
  - dismiss -> restore dismissed notification from pre_state
  - clear   -> restore all cleared notifications from pre_state snapshot
  - reply   -> irreversible; supports_rollback = False
"""
from typing import Any, Mapping

from core.android.bridge.contracts import NotificationBridge
from core.android.capabilities.base import BaseAndroidCapability
from core.android.models import (
    CapabilityCategory, CapabilityDescriptor, ConfirmationLevel, SecurityLevel,
)


# ── Read Capability ────────────────────────────────────────────────────────────

class NotificationReadCapability(BaseAndroidCapability):
    """Read-only notification capability."""

    def __init__(self, bridge: NotificationBridge) -> None:
        self._bridge = bridge

    @property
    def descriptor(self) -> CapabilityDescriptor:
        return CapabilityDescriptor(
            id="android.communication.notification.read",
            name="Notification Read",
            description="Reads active notifications.",
            version="1.0.0",
            category=CapabilityCategory.COMMUNICATION,
            security_level=SecurityLevel.NORMAL,
            supported_actions=("notification.read",),
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


# ── Write Capability (dismiss + clear) ────────────────────────────────────────

class NotificationWriteCapability(BaseAndroidCapability):
    """
    Mutation notification capability for dismiss and clear.
    - dismiss -> NORMAL security, NONE confirmation, reversible
    - clear   -> NORMAL security, NONE confirmation, reversible
    """

    _REVERSIBLE_ACTIONS = frozenset({
        "notification.dismiss",
        "notification.clear",
    })

    def __init__(self, bridge: NotificationBridge) -> None:
        self._bridge = bridge

    @property
    def descriptor(self) -> CapabilityDescriptor:
        return CapabilityDescriptor(
            id="android.communication.notification.write",
            name="Notification Control",
            description="Dismisses or clears notifications. Both actions are reversible.",
            version="1.0.0",
            category=CapabilityCategory.COMMUNICATION,
            security_level=SecurityLevel.NORMAL,
            supported_actions=("notification.dismiss", "notification.clear"),
            is_mutation=True,
            supports_rollback=True,   # dismiss and clear are reversible
            audit_required=True,
            confirmation_level=ConfirmationLevel.NONE,
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

        if action == "notification.dismiss":
            # Restore the single dismissed notification from pre_state
            if data and "pre_state" in data:
                await self._bridge.execute("notification.restore_dismissed", {
                    "notification": data["pre_state"],
                })

        elif action == "notification.clear":
            # Restore all notifications from the pre_state snapshot
            if data and "pre_state" in data:
                await self._bridge.execute("notification.restore_all", {
                    "snapshot": data["pre_state"],
                })


# ── Reply Capability ───────────────────────────────────────────────────────────

class NotificationReplyCapability(BaseAndroidCapability):
    """
    Mutation capability for replying to notifications.
    - reply -> HIGH security, USER confirmation, irreversible.

    Consistent with other irreversible Pack C communication actions
    (phone calls, SMS send).
    """

    def __init__(self, bridge: NotificationBridge) -> None:
        self._bridge = bridge

    @property
    def descriptor(self) -> CapabilityDescriptor:
        return CapabilityDescriptor(
            id="android.communication.notification.reply",
            name="Notification Reply",
            description="Replies to a notification. This action is irreversible.",
            version="1.0.0",
            category=CapabilityCategory.COMMUNICATION,
            security_level=SecurityLevel.HIGH,
            supported_actions=("notification.reply",),
            is_mutation=True,
            supports_rollback=False,   # reply is irreversible
            audit_required=True,
            confirmation_level=ConfirmationLevel.USER,
            idempotent=False,
        )

    async def _execute_internal(self, action: str, arguments: Mapping[str, Any]) -> Mapping[str, Any]:
        return await self._bridge.execute(action, arguments)

    def supports_rollback(self, arguments: Mapping[str, Any]) -> bool:
        # Reply is always irreversible
        return False


# Legacy alias
NotificationCapability = NotificationReadCapability
