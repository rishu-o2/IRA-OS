import pytest
from core.android.bridge.system import MockSystemBridge
from core.android.capabilities.vibrate import VibrateCapability
from core.android.capabilities.exceptions import InvalidArgumentError
from core.android.models import CapabilityCategory

@pytest.fixture
def bridge():
    return MockSystemBridge()

@pytest.fixture
def capability(bridge):
    return VibrateCapability(bridge)

def test_descriptor(capability):
    desc = capability.descriptor
    assert desc.id == "android.device.vibrate"
    assert desc.category == CapabilityCategory.DEVICE
    assert desc.is_mutation is True
    assert desc.supports_rollback is True
    assert "system.vibrate.start" in desc.supported_actions

@pytest.mark.anyio
async def test_vibrate_start(capability, bridge):
    assert bridge._is_vibrating is False
    result = await capability.execute_action({"action": "system.vibrate.start", "duration_ms": 500})
    assert result.data["success"] is True
    assert bridge._is_vibrating is True

@pytest.mark.anyio
async def test_vibrate_start_validation(capability):
    result = await capability.execute_action({"action": "system.vibrate.start"}) # Missing duration
    assert result.success is False
    assert result.error_code == "InvalidArgumentError"
    
    result = await capability.execute_action({"action": "system.vibrate.start", "duration_ms": -50}) # Negative
    assert result.success is False
    assert result.error_code == "InvalidArgumentError"
        
    result = await capability.execute_action({"action": "system.vibrate.start", "duration_ms": "abc"}) # Invalid
    assert result.success is False
    assert result.error_code == "InvalidArgumentError"

    result = await capability.execute_action({"action": "system.vibrate.start", "duration_ms": True}) # Bool
    assert result.success is False
    assert result.error_code == "InvalidArgumentError"

@pytest.mark.anyio
async def test_vibrate_cancel(capability, bridge):
    bridge._is_vibrating = True
    result = await capability.execute_action({"action": "system.vibrate.cancel"})
    assert result.data["success"] is True
    assert bridge._is_vibrating is False

@pytest.mark.anyio
async def test_vibrate_rollback(capability, bridge):
    bridge._is_vibrating = False
    
    # Simulate start action
    await capability.execute_action({"action": "system.vibrate.start", "duration_ms": 500})
    assert bridge._is_vibrating is True
    
    # Rollback start -> should cancel
    await capability.rollback({"action": "system.vibrate.start", "duration_ms": 500}, None)
    assert bridge._is_vibrating is False
