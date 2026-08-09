"""
Unit tests for Pack C: SMS Capabilities
Tests descriptor correctness, action handling, security/confirmation levels,
read/write separation, mutation metadata, and rollback (irreversible send, reversible delete).
"""
import pytest
from core.android.bridge.telephony import MockSMSBridge
from core.android.capabilities.sms import SmsReadCapability, SmsWriteCapability
from core.android.models import SecurityLevel, ConfirmationLevel

@pytest.fixture
def anyio_backend():
    return "asyncio"

@pytest.fixture
def sms_bridge():
    return MockSMSBridge()

@pytest.fixture
def read_cap(sms_bridge):
    return SmsReadCapability(sms_bridge)

@pytest.fixture
def write_cap(sms_bridge):
    return SmsWriteCapability(sms_bridge)


# ── Descriptor Tests ───────────────────────────────────────────────────────────

def test_read_descriptor_id(read_cap):
    assert read_cap.descriptor.id == "android.communication.sms.read"

def test_read_is_not_mutation(read_cap):
    assert read_cap.descriptor.is_mutation is False

def test_read_no_rollback_descriptor(read_cap):
    assert read_cap.descriptor.supports_rollback is False

def test_read_security_normal(read_cap):
    assert read_cap.descriptor.security_level == SecurityLevel.NORMAL

def test_read_confirmation_none(read_cap):
    assert read_cap.descriptor.confirmation_level == ConfirmationLevel.NONE

def test_write_descriptor_id(write_cap):
    assert write_cap.descriptor.id == "android.communication.sms.write"

def test_write_is_mutation(write_cap):
    assert write_cap.descriptor.is_mutation is True

def test_write_security_high(write_cap):
    assert write_cap.descriptor.security_level == SecurityLevel.HIGH

def test_write_confirmation_user(write_cap):
    assert write_cap.descriptor.confirmation_level == ConfirmationLevel.USER

def test_write_audit_required(write_cap):
    assert write_cap.descriptor.audit_required is True


# ── Read Action Handling ───────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_read_all_messages(read_cap, sms_bridge):
    result = await read_cap.execute_action({"action": "telephony.sms.read"})
    assert result.success
    assert len(result.data) == 2

@pytest.mark.anyio
async def test_read_single_message(read_cap, sms_bridge):
    result = await read_cap.execute_action({"action": "telephony.sms.read", "message_id": "msg-001"})
    assert result.success
    assert result.data["id"] == "msg-001"

@pytest.mark.anyio
async def test_search_messages(read_cap, sms_bridge):
    result = await read_cap.execute_action({"action": "telephony.sms.search", "query": "hello"})
    assert result.success
    assert any("Hello" in m["body"] for m in result.data)


# ── Write Action Handling ──────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_send_sms(write_cap, sms_bridge):
    result = await write_cap.execute_action({"action": "telephony.sms.send", "number": "+1234567890", "body": "Hi"})
    assert result.success
    assert len(sms_bridge._sent) == 1

@pytest.mark.anyio
async def test_send_sms_missing_body(write_cap):
    result = await write_cap.execute_action({"action": "telephony.sms.send", "number": "+1234567890"})
    assert not result.success

@pytest.mark.anyio
async def test_delete_sms(write_cap, sms_bridge):
    result = await write_cap.execute_action({"action": "telephony.sms.delete", "message_id": "msg-001"})
    assert result.success
    assert "msg-001" not in sms_bridge._inbox

@pytest.mark.anyio
async def test_delete_nonexistent_sms(write_cap):
    result = await write_cap.execute_action({"action": "telephony.sms.delete", "message_id": "nonexistent"})
    assert not result.success


# ── Rollback Tests ─────────────────────────────────────────────────────────────

def test_send_is_irreversible(write_cap):
    assert write_cap.supports_rollback({"action": "telephony.sms.send"}) is False

def test_delete_is_reversible(write_cap):
    assert write_cap.supports_rollback({"action": "telephony.sms.delete"}) is True

@pytest.mark.anyio
async def test_delete_rollback_restores_message(write_cap, sms_bridge):
    result = await write_cap.execute_action({"action": "telephony.sms.delete", "message_id": "msg-002"})
    assert result.success
    assert "msg-002" not in sms_bridge._inbox

    # Rollback should restore the message
    await write_cap.rollback({"action": "telephony.sms.delete"}, result.data)
    assert "msg-002" in sms_bridge._inbox
    assert sms_bridge._inbox["msg-002"]["body"] == "Test message 2"
