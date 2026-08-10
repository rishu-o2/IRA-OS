import pytest
from core.android.bridge.camera import MockCameraBridge
from core.android.capabilities.camera import CameraReadCapability, CameraWriteCapability
from core.android.models import SecurityLevel, ConfirmationLevel

@pytest.fixture
def anyio_backend():
    return "asyncio"

@pytest.fixture
def bridge():
    return MockCameraBridge()

@pytest.fixture
def read_cap(bridge):
    return CameraReadCapability(bridge)

@pytest.fixture
def write_cap(bridge):
    return CameraWriteCapability(bridge)

def test_read_descriptor(read_cap):
    desc = read_cap.descriptor
    assert desc.id == "android.device.camera.read"
    assert not desc.is_mutation
    assert not desc.supports_rollback
    assert desc.security_level == SecurityLevel.NORMAL
    assert desc.confirmation_level == ConfirmationLevel.NONE

def test_write_descriptor(write_cap):
    desc = write_cap.descriptor
    assert desc.id == "android.device.camera.write"
    assert desc.is_mutation
    assert not desc.supports_rollback
    assert desc.security_level == SecurityLevel.HIGH
    assert desc.confirmation_level == ConfirmationLevel.USER
    assert "camera.capture" in desc.supported_actions

@pytest.mark.anyio
async def test_camera_read(read_cap, bridge):
    res = await read_cap.execute_action({"action": "camera.status"})
    assert res.success
    assert res.data["status"] == "idle"

@pytest.mark.anyio
async def test_camera_write_capture(write_cap, bridge):
    res = await write_cap.execute_action({"action": "camera.capture"})
    assert res.success
    assert "media_id" in res.data
    assert len(bridge._media) == 1

def test_irreversible(write_cap):
    assert not write_cap.supports_rollback({"action": "camera.capture"})
