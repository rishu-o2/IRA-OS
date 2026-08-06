from core.events import EventBus
from core.lifecycle.interfaces import HealthCheckable
from core.lifecycle.models import ComponentHealth
from core.lifecycle.states import ComponentState

from .contracts import AndroidRegistry
from .events import AndroidHealthChanged
from .models import AndroidRuntimeStatus


class AndroidHealthTracker(HealthCheckable):
    """
    Separated health and status tracker for the Android Runtime.
    """

    def __init__(self, event_bus: EventBus, registry: AndroidRegistry):
        self._event_bus = event_bus
        self._registry = registry
        self._status = AndroidRuntimeStatus.STOPPED

    async def update_status(self, new_status: AndroidRuntimeStatus, details: str) -> None:
        if self._status == new_status:
            return
            
        previous = self._status
        self._status = new_status
        
        await self._event_bus.publish(
            AndroidHealthChanged(
                payload={"previous": previous.value, "current": new_status.value, "details": details},
                source="AndroidHealthTracker",
                previous_status=previous,
                current_status=new_status,
                details=details,
            )
        )

    async def health_check(self) -> ComponentHealth:
        if self._status == AndroidRuntimeStatus.STOPPED:
            return ComponentHealth(state=ComponentState.STOPPED, details="Android Runtime is stopped.")
            
        try:
            # Check registry
            capabilities = self._registry.get_all()
            return ComponentHealth(
                state=ComponentState.RUNNING, 
                details=f"Android Runtime is running with {len(capabilities)} capabilities."
            )
        except Exception as exc:
            return ComponentHealth(
                state=ComponentState.DEGRADED,
                details=f"Android Runtime health check failed: {exc}"
            )
