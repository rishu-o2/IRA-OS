from typing import Any, Mapping, Optional

from core.android.capabilities.exceptions import UnsupportedPlatformError
from .contracts import LocationBridge


class MockLocationBridge(LocationBridge):
    """Mock implementation of the LocationBridge."""

    async def execute(self, action: str, arguments: Optional[Mapping[str, Any]] = None) -> Any:
        if action == "location.coarse":
            return {"lat": 37.7749, "lon": -122.4194}
        
        raise UnsupportedPlatformError(f"MockLocationBridge does not support action: {action}")
