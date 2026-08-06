import re

with open('tests/core/android/test_capabilities.py', 'r') as f:
    content = f.read()

content = content.replace('MockAndroidBridge', 'MockSystemBridge')

content = re.sub(
    r'@pytest\.fixture\ndef bridge\(\):\n    return MockSystemBridge\(\)',
    r'@pytest.fixture\ndef sys_bridge():\n    return MockSystemBridge()\n\n@pytest.fixture\ndef net_bridge():\n    from core.android.bridge.network import MockNetworkBridge\n    return MockNetworkBridge()\n\n@pytest.fixture\ndef loc_bridge():\n    from core.android.bridge.location import MockLocationBridge\n    return MockLocationBridge()',
    content
)

content = content.replace('test_battery_capability(bridge):', 'test_battery_capability(sys_bridge):')
content = content.replace('cap = BatteryCapability(bridge)', 'cap = BatteryCapability(sys_bridge)')

content = content.replace('test_clipboard_capability(bridge):', 'test_clipboard_capability(sys_bridge):')
content = content.replace('cap = ClipboardCapability(bridge)', 'cap = ClipboardCapability(sys_bridge)')

content = content.replace('test_wifi_capability(bridge):', 'test_wifi_capability(net_bridge):')
content = content.replace('cap = WifiCapability(bridge)', 'cap = WifiCapability(net_bridge)')

content = content.replace('test_bluetooth_capability(bridge):', 'test_bluetooth_capability(net_bridge):')
content = content.replace('cap = BluetoothCapability(bridge)', 'cap = BluetoothCapability(net_bridge)')

content = content.replace('test_location_capability(bridge):', 'test_location_capability(loc_bridge):')
content = content.replace('cap = LocationCapability(bridge)', 'cap = LocationCapability(loc_bridge)')

content = content.replace('test_invalid_action(bridge):', 'test_invalid_action(sys_bridge):')
content = content.replace('cap = BatteryCapability(bridge)', 'cap = BatteryCapability(sys_bridge)')

with open('tests/core/android/test_capabilities.py', 'w') as f:
    f.write(content)
