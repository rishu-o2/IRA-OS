"""
Mock telephony bridges for Pack C: Communication.

Provides stateful mock implementations of CallBridge, SMSBridge, and
ContactsBridge for use in tests and the development environment.

No Android SDK classes are imported. All platform interaction is simulated
in-memory.
"""
import uuid
from typing import Any, Mapping, Optional

from core.android.capabilities.exceptions import UnsupportedPlatformError
from .contracts import CallBridge, SMSBridge, ContactsBridge


# ── MockCallBridge ─────────────────────────────────────────────────────────────

class MockCallBridge(CallBridge):
    """
    Stateful mock for telephony call control.
    Tracks current call status, caller/recipient, and call history.
    """

    def __init__(self) -> None:
        self._status: str = "idle"          # idle | ringing | active | ended
        self._current_number: Optional[str] = None
        self._history: list[dict] = []

    async def execute(self, action: str, arguments: Optional[Mapping[str, Any]] = None) -> Any:
        args = arguments or {}

        if action == "telephony.phone.status":
            return {
                "status": self._status,
                "number": self._current_number,
            }

        elif action == "telephony.phone.call":
            number = args.get("number")
            if not number:
                raise ValueError("telephony.phone.call requires 'number' argument.")
            pre_state = {"status": self._status, "number": self._current_number}
            self._status = "active"
            self._current_number = number
            self._history.append({"event": "call", "number": number})
            return {"status": self._status, "number": self._current_number, "pre_state": pre_state}

        elif action == "telephony.phone.end":
            pre_state = {"status": self._status, "number": self._current_number}
            self._history.append({"event": "end", "number": self._current_number})
            self._status = "ended"
            self._current_number = None
            return {"status": self._status, "pre_state": pre_state}

        elif action == "telephony.phone.reject":
            pre_state = {"status": self._status, "number": self._current_number}
            self._history.append({"event": "reject", "number": self._current_number})
            self._status = "idle"
            self._current_number = None
            return {"status": self._status, "pre_state": pre_state}

        raise UnsupportedPlatformError(f"MockCallBridge does not support action: {action}")


# ── MockSMSBridge ──────────────────────────────────────────────────────────────

class MockSMSBridge(SMSBridge):
    """
    Stateful mock for SMS messaging.
    Maintains inbox, sent messages, and a soft-delete store for rollback.
    """

    def __init__(self) -> None:
        self._inbox: dict[str, dict] = {
            "msg-001": {"id": "msg-001", "from": "+1111111111", "body": "Hello from IRA test"},
            "msg-002": {"id": "msg-002", "from": "+2222222222", "body": "Test message 2"},
        }
        self._sent: list[dict] = []
        self._deleted: dict[str, dict] = {}   # message_id -> message (for rollback)

    async def execute(self, action: str, arguments: Optional[Mapping[str, Any]] = None) -> Any:
        args = arguments or {}

        if action == "telephony.sms.read":
            message_id = args.get("message_id")
            if message_id:
                msg = self._inbox.get(message_id)
                if not msg:
                    raise ValueError(f"Message '{message_id}' not found.")
                return msg.copy()
            return [m.copy() for m in self._inbox.values()]

        elif action == "telephony.sms.search":
            query = (args.get("query") or "").lower()
            return [m.copy() for m in self._inbox.values() if query in m["body"].lower()]

        elif action == "telephony.sms.send":
            number = args.get("number")
            body = args.get("body")
            if not number or not body:
                raise ValueError("telephony.sms.send requires 'number' and 'body'.")
            msg = {"id": str(uuid.uuid4()), "to": number, "body": body}
            self._sent.append(msg)
            return {"sent": True, "message": msg.copy()}

        elif action == "telephony.sms.delete":
            message_id = args.get("message_id")
            if not message_id:
                raise ValueError("telephony.sms.delete requires 'message_id'.")
            msg = self._inbox.get(message_id)
            if not msg:
                raise ValueError(f"Message '{message_id}' not found in inbox.")
            pre_state = msg.copy()
            del self._inbox[message_id]
            self._deleted[message_id] = pre_state
            return {"deleted": True, "message_id": message_id, "pre_state": pre_state}

        elif action == "telephony.sms.restore":
            message_id = args.get("message_id")
            msg = args.get("message")
            if message_id and msg:
                self._inbox[message_id] = msg.copy()
                if message_id in self._deleted:
                    del self._deleted[message_id]
            return {"restored": True, "message_id": message_id}

        raise UnsupportedPlatformError(f"MockSMSBridge does not support action: {action}")


# ── MockContactsBridge ─────────────────────────────────────────────────────────

class MockContactsBridge(ContactsBridge):
    """
    Stateful mock for contacts management.
    Supports full CRUD with pre-state capture for rollback.
    """

    def __init__(self) -> None:
        self._contacts: dict[str, dict] = {
            "c-001": {"id": "c-001", "name": "Alice", "number": "+1000000001"},
            "c-002": {"id": "c-002", "name": "Bob",   "number": "+1000000002"},
        }

    def _all_contacts(self) -> list[dict]:
        return [c.copy() for c in self._contacts.values()]

    async def execute(self, action: str, arguments: Optional[Mapping[str, Any]] = None) -> Any:
        args = arguments or {}

        if action == "telephony.contacts.read":
            contact_id = args.get("contact_id")
            if contact_id:
                contact = self._contacts.get(contact_id)
                if not contact:
                    raise ValueError(f"Contact '{contact_id}' not found.")
                return contact.copy()
            return self._all_contacts()

        elif action == "telephony.contacts.search":
            query = (args.get("query") or "").lower()
            return [
                c.copy() for c in self._contacts.values()
                if query in c["name"].lower() or query in c["number"]
            ]

        elif action == "telephony.contacts.create":
            name = args.get("name")
            number = args.get("number")
            if not name or not number:
                raise ValueError("telephony.contacts.create requires 'name' and 'number'.")
            contact_id = str(uuid.uuid4())
            contact = {"id": contact_id, "name": name, "number": number}
            self._contacts[contact_id] = contact
            return {"created": True, "contact": contact.copy(), "contact_id": contact_id}

        elif action == "telephony.contacts.update":
            contact_id = args.get("contact_id")
            if not contact_id:
                raise ValueError("telephony.contacts.update requires 'contact_id'.")
            existing = self._contacts.get(contact_id)
            if not existing:
                raise ValueError(f"Contact '{contact_id}' not found.")
            pre_state = existing.copy()
            updated = existing.copy()
            if "name" in args:
                updated["name"] = args["name"]
            if "number" in args:
                updated["number"] = args["number"]
            self._contacts[contact_id] = updated
            return {"updated": True, "contact": updated.copy(), "pre_state": pre_state}

        elif action == "telephony.contacts.delete":
            contact_id = args.get("contact_id")
            if not contact_id:
                raise ValueError("telephony.contacts.delete requires 'contact_id'.")
            existing = self._contacts.get(contact_id)
            if not existing:
                raise ValueError(f"Contact '{contact_id}' not found.")
            pre_state = existing.copy()
            del self._contacts[contact_id]
            return {"deleted": True, "contact_id": contact_id, "pre_state": pre_state}

        elif action == "telephony.contacts.restore":
            contact = args.get("contact")
            if contact:
                self._contacts[contact["id"]] = contact.copy()
            return {"restored": True}

        elif action == "telephony.contacts.remove":
            contact_id = args.get("contact_id")
            if contact_id and contact_id in self._contacts:
                del self._contacts[contact_id]
            return {"removed": True, "contact_id": contact_id}

        raise UnsupportedPlatformError(f"MockContactsBridge does not support action: {action}")
