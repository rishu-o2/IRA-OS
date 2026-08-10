from typing import Any, Mapping, Optional
from core.android.bridge.contracts import MicrophoneBridge
from core.android.exceptions import AndroidAdapterError
import uuid

class MockMicrophoneBridge(MicrophoneBridge):
    def __init__(self):
        self._status = "idle"
        self._recordings = {}

    async def execute(self, action: str, arguments: Optional[Mapping[str, Any]] = None) -> Any:
        args = arguments or {}
        
        if action == "microphone.status":
            return {"status": self._status}
            
        elif action == "microphone.record.start":
            if self._status != "idle":
                raise AndroidAdapterError("Microphone is already recording")
            self._status = "recording"
            return {"success": True}
            
        elif action == "microphone.record.stop":
            if self._status != "recording":
                raise AndroidAdapterError("Microphone is not recording")
            self._status = "idle"
            rec_id = f"rec-{uuid.uuid4().hex[:8]}"
            self._recordings[rec_id] = {"id": rec_id, "status": "completed"}
            return {"recording_id": rec_id}
            
        raise AndroidAdapterError(f"Unsupported action: {action}")
