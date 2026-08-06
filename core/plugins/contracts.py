from abc import ABC, abstractmethod
from typing import List, Optional

from core.lifecycle.models import ComponentHealth

from .models import PluginDescriptor, PluginMetadata, PluginRequest, PluginResult, PluginStatus


class PluginValidator(ABC):
    """Validates plugin manifests and metadata."""

    @abstractmethod
    def validate(self, metadata: PluginMetadata) -> bool:
        """Returns True if the metadata is well-formed and valid."""
        pass


class PluginLoader(ABC):
    """Discovers and loads plugins from storage or network."""

    @abstractmethod
    def discover(self) -> List[PluginMetadata]:
        """Scans for available plugins and returns their metadata."""
        pass


class PluginRegistry(ABC):
    """In-memory registry of known plugins."""

    @abstractmethod
    def register(self, descriptor: PluginDescriptor) -> None:
        pass

    @abstractmethod
    def unregister(self, plugin_id: str) -> bool:
        pass

    @abstractmethod
    def lookup(self, plugin_id: str) -> Optional[PluginDescriptor]:
        pass

    @abstractmethod
    def enumerate(self) -> List[PluginDescriptor]:
        pass


class PluginHealthTracker(ABC):
    """Tracks the health of the plugin subsystem."""

    @abstractmethod
    def set_available(self, available: bool) -> None:
        pass

    @abstractmethod
    def check_health(self) -> ComponentHealth:
        pass


class PluginManager(ABC):
    """
    Orchestrates the canonical Plugin pipeline.
    """

    @abstractmethod
    async def start(self) -> None:
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        pass

    @abstractmethod
    async def health_check(self) -> ComponentHealth:
        pass

    @abstractmethod
    async def discover(self) -> None:
        """Trigger discovery of new plugins."""
        pass

    @abstractmethod
    async def load(self, request: PluginRequest) -> PluginResult:
        """Load a discovered plugin into memory."""
        pass

    @abstractmethod
    async def unload(self, plugin_id: str) -> PluginResult:
        """Unload a plugin from memory."""
        pass

    @abstractmethod
    async def enable(self, plugin_id: str) -> PluginResult:
        """Enable a loaded plugin so its capabilities are active."""
        pass

    @abstractmethod
    async def disable(self, plugin_id: str) -> PluginResult:
        """Disable an enabled plugin."""
        pass

    @abstractmethod
    async def status(self, plugin_id: str) -> PluginStatus:
        """Retrieve the operational status of a plugin."""
        pass

    @abstractmethod
    async def plugins(self) -> List[PluginDescriptor]:
        """List all registered plugins."""
        pass
