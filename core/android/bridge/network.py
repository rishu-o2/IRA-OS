from typing import Any, Mapping, Optional

from core.android.capabilities.exceptions import UnsupportedPlatformError
from .contracts import NetworkBridge


class MockNetworkBridge(NetworkBridge):
    """
    Mock implementation of the NetworkBridge.
    Maintains simulated state for network radios and enforces cascading rules
    (e.g., Airplane mode disables others).
    """

    def __init__(self):
        # Initial states
        self._state = {
            "wifi": {"enabled": True, "connected": False, "ssid": None},
            "bluetooth": {"enabled": False, "paired_devices": []},
            "mobile_data": {"enabled": True},
            "hotspot": {"enabled": False},
            "airplane_mode": {"enabled": False}
        }

    async def execute(self, action: str, arguments: Optional[Mapping[str, Any]] = None) -> Any:
        # Helper to capture pre-state of all radios (needed for airplane mode rollback)
        def _get_full_state():
            return {k: v.copy() for k, v in self._state.items()}

        if action == "network.wifi.status":
            return self._state["wifi"].copy()
        elif action == "network.wifi.enable":
            self._state["wifi"]["enabled"] = True
            return self._state["wifi"].copy()
        elif action == "network.wifi.disable":
            self._state["wifi"]["enabled"] = False
            self._state["wifi"]["connected"] = False
            self._state["wifi"]["ssid"] = None
            return self._state["wifi"].copy()
        elif action == "network.wifi.connect":
            if not self._state["wifi"]["enabled"]:
                raise RuntimeError("Cannot connect to WiFi while it is disabled.")
            ssid = (arguments or {}).get("ssid", "unknown")
            self._state["wifi"]["connected"] = True
            self._state["wifi"]["ssid"] = ssid
            return self._state["wifi"].copy()
        elif action == "network.wifi.disconnect":
            self._state["wifi"]["connected"] = False
            self._state["wifi"]["ssid"] = None
            return self._state["wifi"].copy()
        
        elif action == "network.bluetooth.status":
            return self._state["bluetooth"].copy()
        elif action == "network.bluetooth.enable":
            self._state["bluetooth"]["enabled"] = True
            return self._state["bluetooth"].copy()
        elif action == "network.bluetooth.disable":
            self._state["bluetooth"]["enabled"] = False
            return self._state["bluetooth"].copy()
        elif action == "network.bluetooth.pair":
            if not self._state["bluetooth"]["enabled"]:
                raise RuntimeError("Cannot pair Bluetooth while it is disabled.")
            device_id = (arguments or {}).get("device_id")
            if device_id and device_id not in self._state["bluetooth"]["paired_devices"]:
                self._state["bluetooth"]["paired_devices"].append(device_id)
            return self._state["bluetooth"].copy()
        elif action == "network.bluetooth.unpair":
            device_id = (arguments or {}).get("device_id")
            if device_id in self._state["bluetooth"]["paired_devices"]:
                self._state["bluetooth"]["paired_devices"].remove(device_id)
            return self._state["bluetooth"].copy()

        elif action == "network.mobile_data.status":
            return self._state["mobile_data"].copy()
        elif action == "network.mobile_data.enable":
            self._state["mobile_data"]["enabled"] = True
            return self._state["mobile_data"].copy()
        elif action == "network.mobile_data.disable":
            self._state["mobile_data"]["enabled"] = False
            return self._state["mobile_data"].copy()

        elif action == "network.hotspot.status":
            return self._state["hotspot"].copy()
        elif action == "network.hotspot.enable":
            # Cascading effect: Hotspot turns off WiFi
            pre_state = _get_full_state()
            self._state["hotspot"]["enabled"] = True
            self._state["wifi"]["enabled"] = False
            self._state["wifi"]["connected"] = False
            self._state["wifi"]["ssid"] = None
            return {"status": self._state["hotspot"].copy(), "pre_state": pre_state}
        elif action == "network.hotspot.disable":
            pre_state = _get_full_state()
            self._state["hotspot"]["enabled"] = False
            # Does not auto-restore WiFi
            return {"status": self._state["hotspot"].copy(), "pre_state": pre_state}

        elif action == "network.airplane.status":
            return self._state["airplane_mode"].copy()
        elif action == "network.airplane.enable":
            # Cascading effect: Airplane mode turns off everything else
            pre_state = _get_full_state()
            self._state["airplane_mode"]["enabled"] = True
            self._state["wifi"]["enabled"] = False
            self._state["wifi"]["connected"] = False
            self._state["wifi"]["ssid"] = None
            self._state["bluetooth"]["enabled"] = False
            self._state["mobile_data"]["enabled"] = False
            self._state["hotspot"]["enabled"] = False
            return {"status": self._state["airplane_mode"].copy(), "pre_state": pre_state}
        elif action == "network.airplane.disable":
            pre_state = _get_full_state()
            self._state["airplane_mode"]["enabled"] = False
            # Does not auto-restore other radios
            return {"status": self._state["airplane_mode"].copy(), "pre_state": pre_state}
            
        # Support for rollback by forcing state from pre_state payload
        elif action == "network.state.restore":
            state = (arguments or {}).get("state")
            if state:
                # Only update radios that are present in the restore state
                for radio, values in state.items():
                    if radio in self._state:
                        self._state[radio] = values.copy()
            return {"status": "restored", "current_state": _get_full_state()}
            
        # fallback for old generic tests in test_capabilities.py
        elif action == "wifi.read":
            return {"enabled": True, "ssid": "IRA_OS_WIFI"}
        elif action == "bluetooth.read":
            return {"enabled": False}

        raise UnsupportedPlatformError(f"MockNetworkBridge does not support action: {action}")
