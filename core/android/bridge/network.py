from typing import Any, Mapping, Optional

from core.android.capabilities.exceptions import UnsupportedPlatformError
from .contracts import NetworkBridge


class MockNetworkBridge(NetworkBridge):
    """Mock implementation of the NetworkBridge."""

    async def execute(self, action: str, arguments: Optional[Mapping[str, Any]] = None) -> Any:
        if action == "wifi.read":
            return {"enabled": True, "ssid": "IRA_OS_WIFI"}
        elif action == "bluetooth.read":
            return {"enabled": False}
        
        raise UnsupportedPlatformError(f"MockNetworkBridge does not support action: {action}")
