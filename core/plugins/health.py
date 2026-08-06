from core.lifecycle.models import ComponentHealth
from core.lifecycle.states import ComponentState

from .contracts import PluginHealthTracker


class DefaultPluginHealthTracker(PluginHealthTracker):
    """
    Tracks the health of the plugin subsystem.
    """
    def __init__(self) -> None:
        self._available = False

    def set_available(self, available: bool) -> None:
        self._available = available

    def check_health(self) -> ComponentHealth:
        if not self._available:
            return ComponentHealth(state=ComponentState.STOPPED, details="Plugin Framework is stopped.")
        
        # In a real implementation we would check loader, registry, validator availability here
        return ComponentHealth(state=ComponentState.RUNNING, details="Plugin Framework is healthy.")
