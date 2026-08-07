import pytest
from core.android.bridge.network import MockNetworkBridge
from core.android.capabilities.mobile_data import MobileDataCapability
from core.android.capabilities.hotspot import HotspotCapability
from core.android.capabilities.airplane_mode import AirplaneModeCapability

@pytest.fixture
def bridge():
    return MockNetworkBridge()

@pytest.mark.anyio
async def test_mobile_data(bridge):
    cap = MobileDataCapability(bridge)
    res = await cap._execute_internal("network.mobile_data.disable", {})
    assert res["status"]["enabled"] is False
    assert res["pre_state"]["mobile_data"]["enabled"] is True

@pytest.mark.anyio
async def test_hotspot_cascading(bridge):
    cap = HotspotCapability(bridge)
    # Turn hotspot on -> should disable wifi
    res = await cap._execute_internal("network.hotspot.enable", {})
    assert res["status"]["enabled"] is True
    assert res["pre_state"]["wifi"]["enabled"] is True # wifi was on
    assert res["pre_state"]["hotspot"]["enabled"] is False
    
    wifi_status = await bridge.execute("network.wifi.status")
    assert wifi_status["enabled"] is False # cascaded

@pytest.mark.anyio
async def test_airplane_mode_cascading(bridge):
    cap = AirplaneModeCapability(bridge)
    # Turn airplane mode on -> should disable wifi, bluetooth, mobile data, hotspot
    # Let's turn bluetooth on first
    await bridge.execute("network.bluetooth.enable")
    
    res = await cap._execute_internal("network.airplane.enable", {})
    assert res["status"]["enabled"] is True
    
    # Assert pre_state captured the active radios
    assert res["pre_state"]["wifi"]["enabled"] is True
    assert res["pre_state"]["bluetooth"]["enabled"] is True
    
    # Assert cascaded changes on the bridge
    wifi_status = await bridge.execute("network.wifi.status")
    bt_status = await bridge.execute("network.bluetooth.status")
    assert wifi_status["enabled"] is False
    assert bt_status["enabled"] is False
