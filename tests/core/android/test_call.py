"""
Unit tests for Pack C: Phone Call Capabilities
Tests descriptor correctness, action handling, security/confirmation levels,
read/write separation, and rollback behavior (irreversible for all write actions).
"""
import pytest
from core.android.bridge.telephony import MockCallBridge
from core.android.capabilities.call import PhoneReadCapability, PhoneWriteCapability
from core.android.models import SecurityLevel, ConfirmationLevel


@pytest.fixture
def call_bridge():
    return MockCallBridge()

@pytest.fixture
def read_cap(call_bridge):
    return PhoneReadCapability(call_bridge)

@pytest.fixture
def write_cap(call_bridge):
    return PhoneWriteCapability(call_bridge)


# ── Descriptor Tests ───────────────────────────────────────────────────────────

def test_read_descriptor_id(read_cap):
    assert read_cap.descriptor.id == "android.communication.phone.read"

def test_read_descriptor_not_mutation(read_cap):
    assert read_cap.descriptor.is_mutation is False

def test_read_descriptor_no_rollback(read_cap):
    assert read_cap.descriptor.supports_rollback is False

def test_read_descriptor_security_normal(read_cap):
    assert read_cap.descriptor.security_level == SecurityLevel.NORMAL

def test_read_descriptor_confirmation_none(read_cap):
    assert read_cap.descriptor.confirmation_level == ConfirmationLevel.NONE

def test_write_descriptor_id(write_cap):
    assert write_cap.descriptor.id == "android.communication.phone.write"

def test_write_descriptor_is_mutation(write_cap):
    assert write_cap.descriptor.is_mutation is True

def test_write_descriptor_no_rollback(write_cap):
    assert write_cap.descriptor.supports_rollback is False

def test_write_descriptor_security_high(write_cap):
    assert write_cap.descriptor.security_level == SecurityLevel.HIGH

def test_write_descriptor_confirmation_user(write_cap):
    assert write_cap.descriptor.confirmation_level == ConfirmationLevel.USER

def test_write_descriptor_audit_required(write_cap):
    assert write_cap.descriptor.audit_required is True

def test_write_descriptor_supported_actions(write_cap):
    actions = set(write_cap.descriptor.supported_actions)
    assert "telephony.phone.call" in actions
    assert "telephony.phone.end" in actions
    assert "telephony.phone.reject" in actions


# ── Action Handling ────────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_read_status_idle(read_cap, call_bridge):
    result = await read_cap.execute_action({"action": "telephony.phone.status"})
    assert result.success
    assert result.data["status"] == "idle"

@pytest.mark.anyio
async def test_write_make_call(write_cap, call_bridge):
    result = await write_cap.execute_action({"action": "telephony.phone.call", "number": "+9999999999"})
    assert result.success
    assert call_bridge._status == "active"
    assert call_bridge._current_number == "+9999999999"

@pytest.mark.anyio
async def test_write_end_call(write_cap, call_bridge):
    call_bridge._status = "active"
    call_bridge._current_number = "+9999999999"
    result = await write_cap.execute_action({"action": "telephony.phone.end"})
    assert result.success
    assert call_bridge._status == "ended"

@pytest.mark.anyio
async def test_write_reject_call(write_cap, call_bridge):
    call_bridge._status = "ringing"
    result = await write_cap.execute_action({"action": "telephony.phone.reject"})
    assert result.success
    assert call_bridge._status == "idle"

@pytest.mark.anyio
async def test_write_call_missing_number(write_cap):
    result = await write_cap.execute_action({"action": "telephony.phone.call"})
    assert not result.success

@pytest.mark.anyio
async def test_write_unsupported_action(write_cap):
    result = await write_cap.execute_action({"action": "telephony.phone.invalid"})
    assert not result.success


# ── Rollback Tests ─────────────────────────────────────────────────────────────

def test_write_supports_rollback_false_for_all_actions(write_cap):
    for action in ("telephony.phone.call", "telephony.phone.end", "telephony.phone.reject"):
        assert write_cap.supports_rollback({"action": action}) is False


@pytest.fixture
def anyio_backend():
    return "asyncio"
