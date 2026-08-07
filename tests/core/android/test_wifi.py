import pytest
from core.android.bridge.network import MockNetworkBridge
from core.android.capabilities.wifi import WifiCapability

@pytest.fixture
def bridge():
    return MockNetworkBridge()

@pytest.fixture
def capability(bridge):
    return WifiCapability(bridge)

@pytest.mark.anyio
async def test_wifi_status(capability, bridge):
    res = await capability._execute_internal("network.wifi.status", {})
    assert res["enabled"] is True

@pytest.mark.anyio
async def test_wifi_enable_disable(capability, bridge):
    # Disable
    res = await capability._execute_internal("network.wifi.disable", {})
    assert res["status"]["enabled"] is False
    assert res["pre_state"]["wifi"]["enabled"] is True
    
    # Enable
    res2 = await capability._execute_internal("network.wifi.enable", {})
    assert res2["status"]["enabled"] is True
    assert res2["pre_state"]["wifi"]["enabled"] is False

@pytest.mark.anyio
async def test_wifi_rollback_precise(capability, bridge):
    # Simulate a failed operation that returned pre_state
    class FakeResult:
        def __init__(self, data):
            self.data = data
            
    original_result = FakeResult({"status": {"enabled": False}, "pre_state": {"wifi": {"enabled": True, "connected": False, "ssid": None}}})
    
    # Run rollback
    await capability.rollback({"action": "network.wifi.disable"}, original_result)
    
    # Verify restored
    status = await bridge.execute("network.wifi.status")
    assert status["enabled"] is True
