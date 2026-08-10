import pytest
from core.android.bridge.microphone import MockMicrophoneBridge
from core.android.capabilities.microphone import MicrophoneReadCapability, MicrophoneWriteCapability
from core.android.models import SecurityLevel, ConfirmationLevel

@pytest.fixture
def anyio_backend():
    return "asyncio"

@pytest.fixture
def bridge():
    return MockMicrophoneBridge()

@pytest.fixture
def read_cap(bridge):
    return MicrophoneReadCapability(bridge)

@pytest.fixture
def write_cap(bridge):
    return MicrophoneWriteCapability(bridge)

def test_read_descriptor(read_cap):
    desc = read_cap.descriptor
    assert desc.id == "android.device.microphone.read"
    assert not desc.is_mutation
    assert not desc.supports_rollback
    assert desc.security_level == SecurityLevel.NORMAL
    assert desc.confirmation_level == ConfirmationLevel.NONE

def test_write_descriptor(write_cap):
    desc = write_cap.descriptor
    assert desc.id == "android.device.microphone.write"
    assert desc.is_mutation
    assert not desc.supports_rollback
    assert desc.security_level == SecurityLevel.HIGH
    assert desc.confirmation_level == ConfirmationLevel.USER
    assert "microphone.record.start" in desc.supported_actions

@pytest.mark.anyio
async def test_microphone_read(read_cap):
    res = await read_cap.execute_action({"action": "microphone.status"})
    assert res.success
    assert res.data["status"] == "idle"

@pytest.mark.anyio
async def test_microphone_write_record(write_cap, bridge):
    res1 = await write_cap.execute_action({"action": "microphone.record.start"})
    assert res1.success
    assert bridge._status == "recording"

    res2 = await write_cap.execute_action({"action": "microphone.record.stop"})
    assert res2.success
    assert "recording_id" in res2.data
    assert bridge._status == "idle"

def test_irreversible(write_cap):
    assert not write_cap.supports_rollback({"action": "microphone.record.start"})
    assert not write_cap.supports_rollback({"action": "microphone.record.stop"})
