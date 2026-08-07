from typing import Any, Mapping, Optional

from core.android.capabilities.exceptions import UnsupportedPlatformError
from .contracts import SystemBridge


class MockSystemBridge(SystemBridge):
    """
    Mock implementation of the SystemBridge.
    Simulates a device service and maintains device state (e.g. for testing).
    """
    
    def __init__(self):
        super().__init__()
        self._flashlight_on = False

    async def execute(self, action: str, arguments: Optional[Mapping[str, Any]] = None) -> Any:
        if action == "battery.read":
            return {"level": 85, "is_charging": False}
        elif action == "clipboard.read":
            return {"text": "mocked clipboard content"}
        elif action == "system.flashlight.status":
            return {"enabled": self._flashlight_on}
        elif action == "system.flashlight.on":
            self._flashlight_on = True
            return {"enabled": True}
        elif action == "system.flashlight.off":
            self._flashlight_on = False
            return {"enabled": False}
        elif action == "system.flashlight.toggle":
            self._flashlight_on = not self._flashlight_on
            return {"enabled": self._flashlight_on}
        
        raise UnsupportedPlatformError(f"MockSystemBridge does not support action: {action}")
