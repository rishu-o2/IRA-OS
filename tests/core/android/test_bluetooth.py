import pytest
from core.android.bridge.network import MockNetworkBridge
from core.android.capabilities.bluetooth import BluetoothCapability

@pytest.fixture
def bridge():
    return MockNetworkBridge()

@pytest.fixture
def capability(bridge):
    return BluetoothCapability(bridge)

@pytest.mark.anyio
async def test_bluetooth_status(capability, bridge):
    res = await capability._execute_internal("network.bluetooth.status", {})
    assert res["enabled"] is False

@pytest.mark.anyio
async def test_bluetooth_enable_disable(capability, bridge):
    res = await capability._execute_internal("network.bluetooth.enable", {})
    assert res["status"]["enabled"] is True
    assert res["pre_state"]["bluetooth"]["enabled"] is False
    
    res2 = await capability._execute_internal("network.bluetooth.disable", {})
    assert res2["status"]["enabled"] is False
    assert res2["pre_state"]["bluetooth"]["enabled"] is True
