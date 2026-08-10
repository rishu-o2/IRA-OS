from typing import Any, Mapping, Optional
from core.android.bridge.contracts import StorageBridge
from core.android.exceptions import AndroidAdapterError

class MockStorageBridge(StorageBridge):
    def __init__(self):
        self._total = 128_000_000_000 # 128GB
        self._used = 40_000_000_000   # 40GB
        self._cache = 5_000_000_000   # 5GB

    async def execute(self, action: str, arguments: Optional[Mapping[str, Any]] = None) -> Any:
        args = arguments or {}
        
        if action == "storage.info":
            return {
                "total": self._total,
                "used": self._used,
                "available": self._total - self._used,
                "cache": self._cache
            }
            
        elif action == "storage.format":
            self._used = 0
            self._cache = 0
            return {"success": True}
            
        elif action == "storage.clear_cache":
            self._used -= self._cache
            if self._used < 0:
                self._used = 0
            self._cache = 0
            return {"success": True}
            
        raise AndroidAdapterError(f"Unsupported action: {action}")
