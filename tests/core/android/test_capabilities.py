import pytest

from core.android.bridge.system import MockSystemBridge
from core.android.bridge.network import MockNetworkBridge
from core.android.bridge.location import MockLocationBridge
from core.android.capabilities.base import BaseAndroidCapability
from core.android.capabilities.battery import BatteryCapability
from core.android.capabilities.bluetooth import BluetoothCapability
from core.android.capabilities.clipboard import ClipboardCapability
from core.android.capabilities.exceptions import InvalidArgumentError, PermissionDeniedError
from core.android.capabilities.location import LocationCapability
from core.android.models import SecurityLevel
from core.android.capabilities.wifi import WifiCapability
from core.android.models import CapabilityDescriptor


class MockFailingBridge(MockSystemBridge):
    async def execute(self, action, arguments=None):
        if action == "battery.read":
            raise ValueError("Simulated bridge crash")
        return await super().execute(action, arguments)

class BadCapability(BaseAndroidCapability):
    def __init__(self, bridge=None):
        self.bridge = bridge

    @property
    def descriptor(self) -> CapabilityDescriptor:
        return CapabilityDescriptor(
            id="test.bad",
            name="Bad",
            description="Bad",
            version="1",
            security_level=SecurityLevel.LOW,
            supported_actions=("read",)
        )

    async def _execute_internal(self, action, arguments):
        if action == "read":
            raise PermissionDeniedError("Missing permission")
        return {}


@pytest.fixture
def sys_bridge():
    return MockSystemBridge()

@pytest.fixture
def net_bridge():
    from core.android.bridge.network import MockNetworkBridge
    return MockNetworkBridge()

@pytest.fixture
def loc_bridge():
    from core.android.bridge.location import MockLocationBridge
    return MockLocationBridge()


@pytest.mark.anyio
async def test_battery_capability(sys_bridge):
    cap = BatteryCapability(sys_bridge)
    assert cap.descriptor.id == "android.device.battery"
    assert cap.descriptor.security_level == SecurityLevel.LOW
    
    result = await cap.execute_action({"action": "read"})
    assert result.success is True
    assert result.data["level"] == 85
    assert result.data["is_charging"] is False


@pytest.mark.anyio
async def test_clipboard_capability(sys_bridge):
    cap = ClipboardCapability(sys_bridge)
    result = await cap.execute_action({})
    assert result.success is True
    assert result.data["text"] == "mocked clipboard content"


@pytest.mark.anyio
async def test_wifi_capability(net_bridge):
    cap = WifiCapability(net_bridge)
    assert "ACCESS_WIFI_STATE" in cap.descriptor.required_permissions
    result = await cap.execute_action({})
    assert result.success is True
    assert result.data["enabled"] is True


@pytest.mark.anyio
async def test_bluetooth_capability(net_bridge):
    cap = BluetoothCapability(net_bridge)
    assert "BLUETOOTH" in cap.descriptor.required_permissions
    result = await cap.execute_action({})
    assert result.success is True
    assert result.data["enabled"] is False


@pytest.mark.anyio
async def test_location_capability(loc_bridge):
    cap = LocationCapability(loc_bridge)
    assert "ACCESS_COARSE_LOCATION" in cap.descriptor.required_permissions
    result = await cap.execute_action({})
    assert result.success is True
    assert "lat" in result.data


@pytest.mark.anyio
async def test_invalid_action(sys_bridge):
    cap = BatteryCapability(sys_bridge)
    result = await cap.execute_action({"action": "explode"})
    assert result.success is False
    assert result.error_code == "InvalidArgumentError"


@pytest.mark.anyio
async def test_error_normalization_capability_error():
    bridge = MockSystemBridge()
    cap = BadCapability(bridge)
    result = await cap.execute_action({"action": "read"})
    assert result.success is False
    assert result.error_code == "PermissionDeniedError"
    assert "Missing permission" in result.error_message


@pytest.mark.anyio
async def test_error_normalization_raw_exception():
    bad_bridge = MockFailingBridge()
    cap = BatteryCapability(bad_bridge)
    result = await cap.execute_action({"action": "read"})
    assert result.success is False
    assert result.error_code == "PlatformExecutionError"
    assert "Simulated bridge crash" in result.error_message
