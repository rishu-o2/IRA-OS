from typing import Any, Mapping, Optional
from core.android.bridge.contracts import DownloadBridge
from core.android.exceptions import AndroidAdapterError
import uuid

class MockDownloadBridge(DownloadBridge):
    def __init__(self):
        self._downloads = {}

    async def execute(self, action: str, arguments: Optional[Mapping[str, Any]] = None) -> Any:
        args = arguments or {}
        
        if action == "downloads.list":
            return {"downloads": list(self._downloads.values())}
            
        elif action == "downloads.status":
            dl_id = args.get("download_id")
            if not dl_id:
                raise AndroidAdapterError("download_id is required")
            if dl_id not in self._downloads:
                raise AndroidAdapterError(f"Download not found: {dl_id}")
            return {"download": self._downloads[dl_id]}
            
        elif action == "downloads.start":
            url = args.get("url")
            if not url:
                raise AndroidAdapterError("url is required")
            
            dl_id = f"dl-{uuid.uuid4().hex[:8]}"
            self._downloads[dl_id] = {"id": dl_id, "url": url, "status": "downloading"}
            return {"download_id": dl_id}
            
        elif action == "downloads.pause":
            dl_id = args.get("download_id")
            if not dl_id or dl_id not in self._downloads:
                raise AndroidAdapterError("Valid download_id is required")
            
            # Reversible: capture pre-state
            pre_state = self._downloads[dl_id]["status"]
            self._downloads[dl_id]["status"] = "paused"
            return {"download_id": dl_id, "pre_state": pre_state}
            
        elif action == "downloads.resume":
            dl_id = args.get("download_id")
            if not dl_id or dl_id not in self._downloads:
                raise AndroidAdapterError("Valid download_id is required")
            
            # Reversible: capture pre-state
            pre_state = self._downloads[dl_id]["status"]
            self._downloads[dl_id]["status"] = "downloading"
            return {"download_id": dl_id, "pre_state": pre_state}
            
        elif action == "downloads.cancel":
            dl_id = args.get("download_id")
            if not dl_id or dl_id not in self._downloads:
                raise AndroidAdapterError("Valid download_id is required")
            
            self._downloads[dl_id]["status"] = "cancelled"
            return {"download_id": dl_id}
            
        elif action == "downloads.delete":
            dl_id = args.get("download_id")
            if not dl_id or dl_id not in self._downloads:
                raise AndroidAdapterError("Valid download_id is required")
            
            del self._downloads[dl_id]
            return {"download_id": dl_id}
            
        # Rollback actions
        elif action == "downloads.restore_status":
            dl_id = args.get("download_id")
            pre_state = args.get("pre_state")
            if dl_id in self._downloads:
                self._downloads[dl_id]["status"] = pre_state
            return {"success": True}
            
        raise AndroidAdapterError(f"Unsupported action: {action}")
