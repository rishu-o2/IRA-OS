from typing import Any, Mapping, Optional
from core.android.bridge.contracts import MediaBridge
from core.android.exceptions import AndroidAdapterError

class MockMediaBridge(MediaBridge):
    def __init__(self):
        self._state = "stopped"
        self._current_media = None

    async def execute(self, action: str, arguments: Optional[Mapping[str, Any]] = None) -> Any:
        args = arguments or {}
        
        if action == "media.status":
            return {"state": self._state, "media": self._current_media}
            
        elif action == "media.play":
            self._state = "playing"
            if "media_id" in args:
                self._current_media = args["media_id"]
            return {"state": self._state}
            
        elif action == "media.pause":
            if self._state == "playing":
                self._state = "paused"
            return {"state": self._state}
            
        elif action == "media.stop":
            self._state = "stopped"
            return {"state": self._state}
            
        raise AndroidAdapterError(f"Unsupported action: {action}")
