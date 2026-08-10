import pytest
from core.android.bridge.media import MockMediaBridge
from core.android.capabilities.media import MediaReadCapability, MediaWriteCapability
from core.android.models import SecurityLevel, ConfirmationLevel

@pytest.fixture
def anyio_backend():
    return "asyncio"

@pytest.fixture
def bridge():
    return MockMediaBridge()

@pytest.fixture
def read_cap(bridge):
    return MediaReadCapability(bridge)

@pytest.fixture
def write_cap(bridge):
    return MediaWriteCapability(bridge)

def test_read_descriptor(read_cap):
    desc = read_cap.descriptor
    assert desc.id == "android.device.media.read"
    assert not desc.is_mutation
    assert not desc.supports_rollback

def test_write_descriptor(write_cap):
    desc = write_cap.descriptor
    assert desc.id == "android.device.media.write"
    assert desc.is_mutation
    assert not desc.supports_rollback
    assert desc.security_level == SecurityLevel.NORMAL
    assert desc.confirmation_level == ConfirmationLevel.NONE

@pytest.mark.anyio
async def test_media_playback(write_cap, bridge):
    res = await write_cap.execute_action({"action": "media.play", "media_id": "song1"})
    assert res.success
    assert bridge._state == "playing"
    assert bridge._current_media == "song1"
    
    res = await write_cap.execute_action({"action": "media.pause"})
    assert res.success
    assert bridge._state == "paused"

    res = await write_cap.execute_action({"action": "media.stop"})
    assert res.success
    assert bridge._state == "stopped"

def test_irreversible(write_cap):
    assert not write_cap.supports_rollback({"action": "media.play"})
