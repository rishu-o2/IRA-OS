from typing import Any, Mapping, Optional

from core.android.capabilities.exceptions import UnsupportedPlatformError
from .contracts import SystemBridge


class MockSystemBridge(SystemBridge):
    """Mock implementation of the SystemBridge."""

    async def execute(self, action: str, arguments: Optional[Mapping[str, Any]] = None) -> Any:
        if action == "battery.read":
            return {"level": 85, "is_charging": False}
        elif action == "clipboard.read":
            return {"text": "mocked clipboard content"}
        
        raise UnsupportedPlatformError(f"MockSystemBridge does not support action: {action}")
