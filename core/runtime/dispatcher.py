from core.lifecycle.interfaces import HealthCheckable
from core.lifecycle.models import ComponentHealth
from core.lifecycle.states import ComponentState

from .interfaces import Capability, CapabilityRegistry, Dispatcher
from .models import ExecutionRequest


class RuntimeDispatcher(Dispatcher, HealthCheckable):
    """Dispatcher for routing execution requests to capabilities."""

    def __init__(self) -> None:
        pass

    async def health_check(self) -> ComponentHealth:
        return ComponentHealth(state=ComponentState.RUNNING, details="Dispatcher is available.")

    def dispatch(self, request: ExecutionRequest, registry: CapabilityRegistry) -> Capability:
        # Simple exact-match routing
        return registry.lookup(request.capability_id)
