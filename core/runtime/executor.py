from typing import Any

from core.lifecycle.interfaces import HealthCheckable
from core.lifecycle.models import ComponentHealth
from core.lifecycle.states import ComponentState

from .exceptions import CapabilityNotFoundError, ExecutionFailedError, ValidationError
from .interfaces import Capability, Executor
from .models import ExecutionContext


class RuntimeExecutor(Executor, HealthCheckable):
    """Executor that invokes capabilities and catches all exceptions."""

    def __init__(self) -> None:
        pass

    async def health_check(self) -> ComponentHealth:
        return ComponentHealth(state=ComponentState.RUNNING, details="Executor is available.")

    async def execute(self, capability: Capability, context: ExecutionContext) -> Any:
        try:
            return await capability.execute(context)
        except Exception as exc:
            # We never leak internal exceptions, we normalize everything into ExecutionFailedError
            raise ExecutionFailedError(f"Capability execution failed: {type(exc).__name__}") from exc
