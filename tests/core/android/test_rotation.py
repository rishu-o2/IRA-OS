import pytest
from core.android.bridge.system import MockSystemBridge
from core.android.capabilities.rotation import RotationCapability
from core.android.capabilities.exceptions import InvalidArgumentError
from core.android.models import CapabilityCategory

@pytest.fixture
def bridge():
    return MockSystemBridge()

@pytest.fixture
def capability(bridge):
    return RotationCapability(bridge)

def test_descriptor(capability):
    desc = capability.descriptor
    assert desc.id == "android.device.rotation"
    assert desc.category == CapabilityCategory.DISPLAY

@pytest.mark.anyio
async def test_rotation_get(capability, bridge):
    bridge._rotation_locked = True
    bridge._rotation_orientation = "LANDSCAPE"
    result = await capability.execute_action({"action": "system.rotation.get"})
    assert result.data["locked"] is True
    assert result.data["orientation"] == "LANDSCAPE"

@pytest.mark.anyio
async def test_rotation_lock(capability, bridge):
    bridge._rotation_locked = False
    bridge._rotation_orientation = "PORTRAIT"
    result = await capability.execute_action({"action": "system.rotation.lock", "orientation": "LANDSCAPE"})
    assert result.data["locked"] is True
    assert result.data["orientation"] == "LANDSCAPE"
    assert result.data["pre_state"]["locked"] is False

@pytest.mark.anyio
async def test_rotation_unlock(capability, bridge):
    bridge._rotation_locked = True
    result = await capability.execute_action({"action": "system.rotation.unlock"})
    assert result.data["locked"] is False

@pytest.mark.anyio
async def test_rotation_lock_invalid(capability):
    result = await capability.execute_action({"action": "system.rotation.lock", "orientation": "UPSIDE_DOWN"})
    assert result.success is False
    assert result.error_code == "InvalidArgumentError"

@pytest.mark.anyio
async def test_rotation_rollback_with_prestate(capability, bridge):
    bridge._rotation_locked = False
    
    result = await capability.execute_action({"action": "system.rotation.lock", "orientation": "LANDSCAPE"})
    await capability.rollback({"action": "system.rotation.lock"}, result)
    
    assert bridge._rotation_locked is False

@pytest.mark.anyio
async def test_rotation_rollback_without_prestate(capability, bridge):
    bridge._rotation_locked = False
    
    # Rollback lock without prestate falls back to unlock
    await capability.rollback({"action": "system.rotation.lock"}, None)
    assert bridge._rotation_locked is False
