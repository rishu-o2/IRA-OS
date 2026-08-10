"""
Unit tests for Pack C: Notification Capabilities
Tests descriptor, read/write separation, mutation metadata, rollback behavior
(dismiss -> reversible, clear -> reversible, reply -> irreversible).
"""
import pytest
from core.android.bridge.notification import MockNotificationBridge
from core.android.capabilities.notification import (
    NotificationReadCapability, 
    NotificationWriteCapability,
    NotificationReplyCapability
)
from core.android.models import SecurityLevel, ConfirmationLevel

@pytest.fixture
def anyio_backend():
    return "asyncio"

@pytest.fixture
def notif_bridge():
    return MockNotificationBridge()

@pytest.fixture
def read_cap(notif_bridge):
    return NotificationReadCapability(notif_bridge)

@pytest.fixture
def write_cap(notif_bridge):
    return NotificationWriteCapability(notif_bridge)

@pytest.fixture
def reply_cap(notif_bridge):
    return NotificationReplyCapability(notif_bridge)


# ── Descriptor Tests ───────────────────────────────────────────────────────────

def test_read_descriptor_id(read_cap):
    assert read_cap.descriptor.id == "android.communication.notification.read"

def test_read_not_mutation(read_cap):
    assert read_cap.descriptor.is_mutation is False

def test_read_security_normal(read_cap):
    assert read_cap.descriptor.security_level == SecurityLevel.NORMAL

def test_read_confirmation_none(read_cap):
    assert read_cap.descriptor.confirmation_level == ConfirmationLevel.NONE


def test_write_descriptor_id(write_cap):
    assert write_cap.descriptor.id == "android.communication.notification.write"

def test_write_is_mutation(write_cap):
    assert write_cap.descriptor.is_mutation is True

def test_write_supports_rollback_descriptor(write_cap):
    assert write_cap.descriptor.supports_rollback is True

def test_write_security_normal(write_cap):
    assert write_cap.descriptor.security_level == SecurityLevel.NORMAL

def test_write_confirmation_none(write_cap):
    # Notification dismiss/clear requires no user confirmation per spec
    assert write_cap.descriptor.confirmation_level == ConfirmationLevel.NONE

def test_write_audit_required(write_cap):
    assert write_cap.descriptor.audit_required is True

def test_write_supported_actions(write_cap):
    actions = set(write_cap.descriptor.supported_actions)
    assert "notification.dismiss" in actions
    assert "notification.clear" in actions
    assert "notification.reply" not in actions


def test_reply_descriptor_id(reply_cap):
    assert reply_cap.descriptor.id == "android.communication.notification.reply"

def test_reply_is_mutation(reply_cap):
    assert reply_cap.descriptor.is_mutation is True

def test_reply_supports_rollback_descriptor(reply_cap):
    assert reply_cap.descriptor.supports_rollback is False

def test_reply_security_high(reply_cap):
    assert reply_cap.descriptor.security_level == SecurityLevel.HIGH

def test_reply_confirmation_user(reply_cap):
    assert reply_cap.descriptor.confirmation_level == ConfirmationLevel.USER

def test_reply_audit_required(reply_cap):
    assert reply_cap.descriptor.audit_required is True

def test_reply_supported_actions(reply_cap):
    actions = set(reply_cap.descriptor.supported_actions)
    assert "notification.reply" in actions


# ── Read Action Handling ───────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_read_notifications(read_cap, notif_bridge):
    result = await read_cap.execute_action({"action": "notification.read"})
    assert result.success
    assert len(result.data) == 3


# ── Write Action Handling ──────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_dismiss_notification(write_cap, notif_bridge):
    result = await write_cap.execute_action({"action": "notification.dismiss", "notification_id": "n-001"})
    assert result.success
    assert "n-001" not in notif_bridge._active

@pytest.mark.anyio
async def test_dismiss_missing_id(write_cap):
    result = await write_cap.execute_action({"action": "notification.dismiss"})
    assert not result.success

@pytest.mark.anyio
async def test_clear_all_notifications(write_cap, notif_bridge):
    result = await write_cap.execute_action({"action": "notification.clear"})
    assert result.success
    assert len(notif_bridge._active) == 0


# ── Reply Action Handling ──────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_reply_notification(reply_cap, notif_bridge):
    result = await reply_cap.execute_action({"action": "notification.reply", "notification_id": "n-002", "text": "Thanks"})
    assert result.success
    assert result.data["replied"] is True

@pytest.mark.anyio
async def test_reply_missing_text(reply_cap):
    result = await reply_cap.execute_action({"action": "notification.reply", "notification_id": "n-001"})
    assert not result.success


# ── Rollback Tests ─────────────────────────────────────────────────────────────

def test_dismiss_is_reversible(write_cap):
    assert write_cap.supports_rollback({"action": "notification.dismiss"}) is True

def test_clear_is_reversible(write_cap):
    assert write_cap.supports_rollback({"action": "notification.clear"}) is True

def test_reply_is_irreversible(reply_cap):
    assert reply_cap.supports_rollback({"action": "notification.reply"}) is False

@pytest.mark.anyio
async def test_dismiss_rollback_restores_notification(write_cap, notif_bridge):
    result = await write_cap.execute_action({"action": "notification.dismiss", "notification_id": "n-001"})
    assert result.success
    assert "n-001" not in notif_bridge._active

    await write_cap.rollback({"action": "notification.dismiss"}, result.data)
    assert "n-001" in notif_bridge._active
    assert notif_bridge._active["n-001"]["title"] == "IRA Test"

@pytest.mark.anyio
async def test_clear_rollback_restores_all_notifications(write_cap, notif_bridge):
    result = await write_cap.execute_action({"action": "notification.clear"})
    assert result.success
    assert len(notif_bridge._active) == 0

    await write_cap.rollback({"action": "notification.clear"}, result.data)
    assert len(notif_bridge._active) == 3

