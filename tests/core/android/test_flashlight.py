import pytest
from core.android.bridge.system import MockSystemBridge
from core.android.capabilities.flashlight import FlashlightCapability
from core.android.models import ConfirmationLevel, SecurityLevel

@pytest.fixture
def anyio_backend():
    return "asyncio"

@pytest.fixture
def mock_bridge():
    return MockSystemBridge()

@pytest.fixture
def flashlight_capability(mock_bridge):
    return FlashlightCapability(mock_bridge)

@pytest.mark.anyio
async def test_descriptor_metadata(flashlight_capability):
    desc = flashlight_capability.descriptor
    assert desc.id == "android.hardware.flashlight"
    assert desc.security_level == SecurityLevel.LOW
    assert desc.is_mutation is True
    assert desc.supports_rollback is True
    assert desc.audit_required is True
    assert desc.confirmation_level == ConfirmationLevel.USER
    assert "system.flashlight.on" in desc.supported_actions

@pytest.mark.anyio
async def test_flashlight_on_off_toggle_status(flashlight_capability, mock_bridge):
    # Initial status
    res = await flashlight_capability.execute_action({"action": "system.flashlight.status"})
    assert res.data["enabled"] is False

    # Turn on
    res = await flashlight_capability.execute_action({"action": "system.flashlight.on"})
    assert res.data["enabled"] is True
    assert mock_bridge._flashlight_on is True

    # Turn off
    res = await flashlight_capability.execute_action({"action": "system.flashlight.off"})
    assert res.data["enabled"] is False
    assert mock_bridge._flashlight_on is False

    # Toggle
    res = await flashlight_capability.execute_action({"action": "system.flashlight.toggle"})
    assert res.data["enabled"] is True
    assert mock_bridge._flashlight_on is True

@pytest.mark.anyio
async def test_supports_rollback(flashlight_capability):
    assert flashlight_capability.supports_rollback({"action": "system.flashlight.on"}) is True
    assert flashlight_capability.supports_rollback({"action": "system.flashlight.off"}) is True
    assert flashlight_capability.supports_rollback({"action": "system.flashlight.toggle"}) is True
    assert flashlight_capability.supports_rollback({"action": "system.flashlight.status"}) is False

@pytest.mark.anyio
async def test_rollback_on_action(flashlight_capability, mock_bridge):
    # If action was 'on', rollback should turn it 'off'
    mock_bridge._flashlight_on = True
    await flashlight_capability.rollback({"action": "system.flashlight.on"}, None)
    assert mock_bridge._flashlight_on is False

@pytest.mark.anyio
async def test_rollback_off_action(flashlight_capability, mock_bridge):
    # If action was 'off', rollback should turn it 'on'
    mock_bridge._flashlight_on = False
    await flashlight_capability.rollback({"action": "system.flashlight.off"}, None)
    assert mock_bridge._flashlight_on is True
