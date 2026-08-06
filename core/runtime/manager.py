from typing import Any

from core.events import EventBus
from core.lifecycle.interfaces import HealthCheckable, LifecycleComponent
from core.lifecycle.models import ComponentHealth
from core.lifecycle.states import ComponentState
from core.logging import Logger

from .events import ExecutionCompleted, ExecutionFailed, ExecutionStarted
from .exceptions import RuntimeSubsystemError, ValidationError
from .interfaces import CapabilityRegistry, Dispatcher, Executor, Validator
from .models import ExecutionContext, ExecutionRequest, ExecutionResult, ExecutionStatus


class RuntimeManager(LifecycleComponent, HealthCheckable):
    """Orchestrates the canonical runtime pipeline."""

    def __init__(
        self,
        validator: Validator,
        registry: CapabilityRegistry,
        dispatcher: Dispatcher,
        executor: Executor,
        event_bus: EventBus,
        logger: Logger,
    ):
        self._validator = validator
        self._registry = registry
        self._dispatcher = dispatcher
        self._executor = executor
        self._event_bus = event_bus
        self._logger = logger
        self._started = False

    async def start(self) -> None:
        if self._started:
            return
        self._logger.info("RuntimeManager starting.")
        self._started = True

    async def shutdown(self) -> None:
        if not self._started:
            return
        self._logger.info("RuntimeManager shutting down.")
        self._started = False

    async def health_check(self) -> ComponentHealth:
        if not self._started:
            return ComponentHealth(state=ComponentState.STOPPED, details="Runtime is stopped.")

        missing = []
        if self._registry is None:
            missing.append("Registry")
        if self._dispatcher is None:
            missing.append("Dispatcher")
        if self._executor is None:
            missing.append("Executor")
        if self._event_bus is None:
            missing.append("Event Bus")

        if missing:
            return ComponentHealth(
                state=ComponentState.DEGRADED,
                details=f"Missing runtime dependencies: {', '.join(missing)}.",
            )

        return ComponentHealth(state=ComponentState.RUNNING, details="Runtime is available.")

    async def execute(self, request: Any) -> ExecutionResult:
        """
        Executes the canonical runtime pipeline:
        1. Execution Request
        2. Validation
        3. Capability Lookup
        4. Dispatch
        5. Execute
        6. Normalize Result
        7. Publish Events
        8. Execution Result
        """
        request_id = getattr(request, "execution_id", "unknown")
        
        try:
            # 2. Validation (initial)
            if not isinstance(request, ExecutionRequest):
                raise ValidationError("Request is not an ExecutionRequest.")
                
            self._validator.validate_request(request)

            # 3. Capability Lookup & 4. Dispatch
            capability = self._dispatcher.dispatch(request, self._registry)

            # 2. Validation (arguments against capability)
            self._validator.validate_arguments(capability, request)

            # Execution Context
            context = ExecutionContext(request=request, capability_metadata=capability.metadata)

            # 7. Publish Events (Started)
            await self._event_bus.publish(
                ExecutionStarted(
                    payload={"execution_id": request.execution_id, "capability_id": request.capability_id},
                    source="RuntimeManager",
                    execution_id=request.execution_id,
                    capability_id=request.capability_id,
                )
            )

            # 5. Execute
            result_data = await self._executor.execute(capability, context)

            # 6. Normalize Result (Success)
            result = ExecutionResult(
                execution_id=request.execution_id,
                success=True,
                status=ExecutionStatus.COMPLETED,
                result_data=result_data,
            )

            # 7. Publish Events (Completed)
            await self._event_bus.publish(
                ExecutionCompleted(
                    payload={"execution_id": request.execution_id, "success": True},
                    source="RuntimeManager",
                    execution_id=request.execution_id,
                    success=True,
                    result_data=result_data,
                )
            )

            # 8. Execution Result
            return result

        except RuntimeSubsystemError as exc:
            return await self._fail(request_id, str(exc))
        except Exception as exc:
            import traceback
            traceback.print_exc()
            return await self._fail(request_id, "Execution failed due to unexpected error.")

    async def _fail(self, execution_id: str, error_message: str) -> ExecutionResult:
        self._logger.error(error_message, execution_id=execution_id)
        
        await self._event_bus.publish(
            ExecutionFailed(
                payload={"execution_id": execution_id, "error": error_message},
                source="RuntimeManager",
                execution_id=execution_id,
                error=error_message,
            )
        )
        
        return ExecutionResult(
            execution_id=execution_id,
            success=False,
            status=ExecutionStatus.FAILED,
            error=error_message,
        )
