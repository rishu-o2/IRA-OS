"""
Mock notification bridge for Pack C: Communication.

Provides a stateful in-memory MockNotificationBridge that supports
reading, dismissing, clearing, and replying to notifications.
Dismissed and cleared notifications are preserved for rollback.
"""
from typing import Any, Mapping, Optional

from core.android.capabilities.exceptions import UnsupportedPlatformError
from .contracts import NotificationBridge


class MockNotificationBridge(NotificationBridge):
    """
    Stateful mock for notification management.

    Maintains:
    - active notifications
    - dismissed notifications (for dismiss-rollback)
    - cleared snapshot (for clear-rollback)
    """

    def __init__(self) -> None:
        self._active: dict[str, dict] = {
            "n-001": {"id": "n-001", "app": "com.ira.test", "title": "IRA Test", "body": "Hello"},
            "n-002": {"id": "n-002", "app": "com.ira.sms",  "title": "New SMS",  "body": "From +123"},
            "n-003": {"id": "n-003", "app": "com.ira.call", "title": "Missed call", "body": "+456"},
        }
        self._dismissed: dict[str, dict] = {}   # notification_id -> notification
        self._pre_clear_snapshot: Optional[dict[str, dict]] = None

    async def execute(self, action: str, arguments: Optional[Mapping[str, Any]] = None) -> Any:
        args = arguments or {}

        if action == "notification.read":
            return [n.copy() for n in self._active.values()]

        elif action == "notification.dismiss":
            notification_id = args.get("notification_id")
            if not notification_id:
                raise ValueError("notification.dismiss requires 'notification_id'.")
            n = self._active.get(notification_id)
            if not n:
                raise ValueError(f"Notification '{notification_id}' not found.")
            pre_state = n.copy()
            del self._active[notification_id]
            self._dismissed[notification_id] = pre_state
            return {"dismissed": True, "notification_id": notification_id, "pre_state": pre_state}

        elif action == "notification.clear":
            # Capture full pre-state of active notifications for rollback
            pre_state = {nid: n.copy() for nid, n in self._active.items()}
            self._pre_clear_snapshot = pre_state
            self._active.clear()
            return {"cleared": True, "count": len(pre_state), "pre_state": pre_state}

        elif action == "notification.reply":
            notification_id = args.get("notification_id")
            text = args.get("text")
            if not notification_id or not text:
                raise ValueError("notification.reply requires 'notification_id' and 'text'.")
            # Reply is irreversible; just record that it happened
            return {"replied": True, "notification_id": notification_id, "text": text}

        elif action == "notification.restore_dismissed":
            # Internal rollback action: restore a single dismissed notification
            notification = args.get("notification")
            if notification:
                nid = notification["id"]
                self._active[nid] = notification.copy()
                if nid in self._dismissed:
                    del self._dismissed[nid]
            return {"restored": True}

        elif action == "notification.restore_all":
            # Internal rollback action: restore all from a pre-state snapshot
            snapshot = args.get("snapshot")
            if snapshot:
                self._active = {nid: n.copy() for nid, n in snapshot.items()}
            return {"restored": True}

        raise UnsupportedPlatformError(f"MockNotificationBridge does not support action: {action}")
