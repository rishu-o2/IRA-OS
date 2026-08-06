from typing import Dict, List, Optional

from .contracts import PluginRegistry
from .models import PluginDescriptor


class InMemoryPluginRegistry(PluginRegistry):
    """
    In-memory storage for plugin descriptors.
    """
    def __init__(self) -> None:
        self._plugins: Dict[str, PluginDescriptor] = {}

    def register(self, descriptor: PluginDescriptor) -> None:
        self._plugins[descriptor.plugin_id] = descriptor

    def unregister(self, plugin_id: str) -> bool:
        if plugin_id in self._plugins:
            del self._plugins[plugin_id]
            return True
        return False

    def lookup(self, plugin_id: str) -> Optional[PluginDescriptor]:
        return self._plugins.get(plugin_id)

    def enumerate(self) -> List[PluginDescriptor]:
        return list(self._plugins.values())
