import pytest
from core.android.bridge.system import MockSystemBridge
from core.android.capabilities.screen_timeout import ScreenTimeoutCapability
from core.android.capabilities.exceptions import InvalidArgumentError
from core.android.models import CapabilityCategory

@pytest.fixture
def bridge():
    return MockSystemBridge()

@pytest.fixture
def capability(bridge):
    return ScreenTimeoutCapability(bridge)

def test_descriptor(capability):
    desc = capability.descriptor
    assert desc.id == "android.device.screen_timeout"
    assert desc.category == CapabilityCategory.DISPLAY

@pytest.mark.anyio
async def test_screen_timeout_get(capability, bridge):
    bridge._screen_timeout_ms = 60000
    result = await capability.execute_action({"action": "system.screen_timeout.get"})
    assert result.data["duration_ms"] == 60000

@pytest.mark.anyio
async def test_screen_timeout_get_supported(capability, bridge):
    result = await capability.execute_action({"action": "system.screen_timeout.get_supported"})
    assert 60000 in result.data["supported"]

@pytest.mark.anyio
async def test_screen_timeout_set_valid(capability, bridge):
    bridge._screen_timeout_ms = 60000
    result = await capability.execute_action({"action": "system.screen_timeout.set", "duration_ms": 120000})
    assert result.data["duration_ms"] == 120000
    assert result.data["pre_state"]["duration_ms"] == 60000

@pytest.mark.anyio
async def test_screen_timeout_set_unsupported(capability, bridge):
    result = await capability.execute_action({"action": "system.screen_timeout.set", "duration_ms": 9999})
    assert result.success is False
    assert result.error_code == "InvalidArgumentError"
    assert "9999 is not supported" in result.error_message

@pytest.mark.anyio
async def test_screen_timeout_set_invalid_type(capability):
    result = await capability.execute_action({"action": "system.screen_timeout.set", "duration_ms": "abc"})
    assert result.success is False
    assert result.error_code == "InvalidArgumentError"

@pytest.mark.anyio
async def test_screen_timeout_rollback_with_prestate(capability, bridge):
    bridge._screen_timeout_ms = 60000
    result = await capability.execute_action({"action": "system.screen_timeout.set", "duration_ms": 120000})
    
    # Rollback uses the precise state
    await capability.rollback({"action": "system.screen_timeout.set"}, result)
    assert bridge._screen_timeout_ms == 60000

@pytest.mark.anyio
async def test_screen_timeout_rollback_without_prestate(capability, bridge):
    bridge._screen_timeout_ms = 120000
    # Rollback without prestate should no-op
    await capability.rollback({"action": "system.screen_timeout.set"}, None)
    assert bridge._screen_timeout_ms == 120000
