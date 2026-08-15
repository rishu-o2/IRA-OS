from typing import Any, Mapping, Optional
from core.android.bridge.contracts import FileBridge
from core.android.exceptions import AndroidAdapterError

class MockFileBridge(FileBridge):
    def __init__(self):
        self._fs = {}

    async def execute(self, action: str, arguments: Optional[Mapping[str, Any]] = None) -> Any:
        args = arguments or {}
        
        if action == "files.read":
            path = args.get("path")
            if not path:
                raise AndroidAdapterError("path is required")
            if path not in self._fs:
                raise AndroidAdapterError(f"File not found: {path}")
            return {"path": path, "content": self._fs[path]["content"]}
            
        elif action == "files.list":
            return {"files": list(self._fs.keys())}
            
        elif action == "files.create":
            path = args.get("path")
            content = args.get("content", "")
            if not path:
                raise AndroidAdapterError("path is required")
            if path in self._fs:
                raise AndroidAdapterError(f"File already exists: {path}")
            self._fs[path] = {"content": content}
            return {"path": path}
            
        elif action == "files.write":
            path = args.get("path")
            content = args.get("content", "")
            if not path:
                raise AndroidAdapterError("path is required")
            if path not in self._fs:
                raise AndroidAdapterError(f"File not found: {path}")
            
            # Reversible: capture pre-state
            pre_state = self._fs[path].copy()
            self._fs[path]["content"] = content
            return {"path": path, "pre_state": pre_state}
            
        elif action == "files.rename":
            src = args.get("source")
            dest = args.get("destination")
            if not src or not dest:
                raise AndroidAdapterError("source and destination are required")
            if src not in self._fs:
                raise AndroidAdapterError(f"File not found: {src}")
            if dest in self._fs:
                raise AndroidAdapterError(f"Destination exists: {dest}")
            
            # Reversible: pre_state is source and dest paths
            self._fs[dest] = self._fs.pop(src)
            return {"source": src, "destination": dest, "pre_state": {"source": src, "destination": dest}}
            
        elif action == "files.move":
            src = args.get("source")
            dest = args.get("destination")
            if not src or not dest:
                raise AndroidAdapterError("source and destination are required")
            if src not in self._fs:
                raise AndroidAdapterError(f"File not found: {src}")
            if dest in self._fs:
                raise AndroidAdapterError(f"Destination exists: {dest}")
                
            self._fs[dest] = self._fs.pop(src)
            return {"source": src, "destination": dest, "pre_state": {"source": src, "destination": dest}}

        elif action == "files.delete":
            path = args.get("path")
            if not path:
                raise AndroidAdapterError("path is required")
            if path not in self._fs:
                raise AndroidAdapterError(f"File not found: {path}")
            
            pre_state = self._fs.pop(path)
            return {"path": path, "pre_state": pre_state}
            
        # Rollback actions
        elif action == "files.restore_delete":
            path = args.get("path")
            pre_state = args.get("pre_state")
            self._fs[path] = pre_state
            return {"success": True}
            
        elif action == "files.restore_write":
            path = args.get("path")
            pre_state = args.get("pre_state")
            self._fs[path] = pre_state
            return {"success": True}
            
        elif action == "files.restore_rename":
            src = args.get("source")
            dest = args.get("destination")
            self._fs[src] = self._fs.pop(dest)
            return {"success": True}
            
        elif action == "files.restore_move":
            src = args.get("source")
            dest = args.get("destination")
            self._fs[src] = self._fs.pop(dest)
            return {"success": True}
            
        raise AndroidAdapterError(f"Unsupported action: {action}")
