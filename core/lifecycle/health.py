from typing import Dict, List, Optional
from datetime import datetime, timezone
from .states import ComponentState
from .models import ComponentHealth


class HealthMonitor:
    """
    Maintains health information for every registered component.
    """
    def __init__(self):
        self._health: Dict[str, ComponentHealth] = {}

    def _update_state(self, name: str, state: ComponentState, details: str = "") -> None:
        """Internal helper to update the component's state."""
        self._health[name] = ComponentHealth(
            state=state,
            details=details,
            timestamp=datetime.now(timezone.utc)
        )

    def healthy(self, name: str, details: str = "") -> None:
        self._update_state(name, ComponentState.RUNNING, details)

    def unhealthy(self, name: str, details: str = "") -> None:
        # We could add an UNHEALTHY or DEGRADED state if needed in the future,
        # but for now, FAILED represents an unhealthy state.
        self._update_state(name, ComponentState.FAILED, details)

    def starting(self, name: str, details: str = "") -> None:
        self._update_state(name, ComponentState.STARTING, details)

    def running(self, name: str, details: str = "") -> None:
        self._update_state(name, ComponentState.RUNNING, details)

    def stopped(self, name: str, details: str = "") -> None:
        self._update_state(name, ComponentState.STOPPED, details)

    def failed(self, name: str, details: str = "") -> None:
        self._update_state(name, ComponentState.FAILED, details)
        
    def booting(self, name: str, details: str = "") -> None:
        self._update_state(name, ComponentState.BOOTING, details)
        
    def shutting_down(self, name: str, details: str = "") -> None:
        self._update_state(name, ComponentState.SHUTTING_DOWN, details)
        
    def created(self, name: str, details: str = "") -> None:
        self._update_state(name, ComponentState.CREATED, details)

    def get_health(self, name: str) -> Optional[ComponentHealth]:
        """Returns the immutable health snapshot for a component."""
        return self._health.get(name)

    def get_all_health(self) -> Dict[str, ComponentHealth]:
        """Returns immutable health snapshots for all components."""
        return dict(self._health)
