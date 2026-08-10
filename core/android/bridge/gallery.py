from typing import Any, Mapping, Optional
from core.android.bridge.contracts import GalleryBridge
from core.android.exceptions import AndroidAdapterError
import uuid

class MockGalleryBridge(GalleryBridge):
    def __init__(self):
        self._assets = {}

    async def execute(self, action: str, arguments: Optional[Mapping[str, Any]] = None) -> Any:
        args = arguments or {}
        
        if action == "gallery.list":
            return {"assets": list(self._assets.values())}
            
        elif action == "gallery.add":
            asset_id = f"img-{uuid.uuid4().hex[:8]}"
            self._assets[asset_id] = {"id": asset_id, "type": args.get("type", "image")}
            return {"asset_id": asset_id}
            
        elif action == "gallery.delete":
            asset_id = args.get("asset_id")
            if not asset_id:
                raise AndroidAdapterError("asset_id is required")
            if asset_id not in self._assets:
                raise AndroidAdapterError(f"Asset not found: {asset_id}")
            
            # Reversible: capture pre-state
            pre_state = self._assets.pop(asset_id)
            return {"asset_id": asset_id, "pre_state": pre_state}
            
        # Rollback actions
        elif action == "gallery.restore_add":
            asset_id = args.get("asset_id")
            if asset_id in self._assets:
                del self._assets[asset_id]
            return {"success": True}
            
        elif action == "gallery.restore_delete":
            asset_id = args.get("asset_id")
            pre_state = args.get("pre_state")
            self._assets[asset_id] = pre_state
            return {"success": True}
            
        raise AndroidAdapterError(f"Unsupported action: {action}")
