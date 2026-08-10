from typing import Any, Mapping, Optional
from core.android.bridge.contracts import CameraBridge
from core.android.exceptions import AndroidAdapterError
import uuid

class MockCameraBridge(CameraBridge):
    def __init__(self):
        self._status = "idle"
        self._media = {}

    async def execute(self, action: str, arguments: Optional[Mapping[str, Any]] = None) -> Any:
        args = arguments or {}
        
        if action == "camera.status":
            return {"status": self._status}
        
        elif action == "camera.capture":
            # Irreversible operation
            self._status = "capturing"
            media_id = f"cam-{uuid.uuid4().hex[:8]}"
            self._media[media_id] = {"id": media_id, "type": "photo"}
            self._status = "idle"
            return {"media_id": media_id}
            
        raise AndroidAdapterError(f"Unsupported action: {action}")
