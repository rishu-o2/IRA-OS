import uuid

from core.events import EventBus
from core.logging import Logger
from core.runtime.interfaces import CapabilityRegistry, Dispatcher, Executor
from core.runtime.models import ExecutionRequest
from core.security.contracts import PermissionManager
from core.security.models import PermissionRequest, PermissionState, SecurityContext, TrustLevel

from .contracts import ExecutionService
from .events import (
    ExecutionAuthorized,
    ExecutionDenied,
    ExecutionDispatched,
    ExecutionFailed,
    ExecutionRequested,
    ExecutionSucceeded,
)
from .exceptions import ExecutionRuntimeError, ExecutionValidationError
from .models import ExecutionCommand, ExecutionOutcome, ExecutionOutcomeStatus


class DefaultExecutionService(ExecutionService):
    """
    The canonical implementation of the ExecutionService kernel.

    This is the single authoritative bridge between Workflow orchestration
    and platform capability execution. It enforces the Security pipeline
    before every dispatch to the Runtime, making it impossible to execute
    a capability without authorization.

    No other subsystem should invoke the RuntimeManager or SecurityManager
    directly for capability execution purposes.
    """

    def __init__(
        self,
        permission_manager: PermissionManager,
        registry: CapabilityRegistry,
        dispatcher: Dispatcher,
        executor: Executor,
        event_bus: EventBus,
        logger: Logger,
    ) -> None:
        self._permission_manager = permission_manager
        self._registry = registry
        self._dispatcher = dispatcher
        self._executor = executor
        self._event_bus = event_bus
        self._logger = logger

    async def execute(self, command: ExecutionCommand) -> ExecutionOutcome:
        """
        Canonical execution pipeline:
          1. Validate command
          2. Publish ExecutionRequested
          3. Request Security authorization
          4. If denied: publish ExecutionDenied, return denied outcome
          5. Publish ExecutionAuthorized
          6. Dispatch to Runtime
          7. Publish ExecutionDispatched
          8. Await result
          9. Publish ExecutionSucceeded / ExecutionFailed
          10. Return ExecutionOutcome
        """
        if not command or not command.command_id or not command.capability_id:
            raise ExecutionValidationError("ExecutionCommand must have a command_id and capability_id.")

        cap_id = command.capability_id
        cmd_id = command.command_id

        # Step 2: Publish requested event
        await self._event_bus.publish(
            ExecutionRequested(
                payload={"command_id": cmd_id, "capability_id": cap_id},
                source="ExecutionService",
                command_id=cmd_id,
                capability_id=cap_id,
            )
        )

        # Step 3: Security authorization
        permission_request = PermissionRequest(
            permission_id=str(uuid.uuid4()),
            capability_id=cap_id,
            context=SecurityContext(
                request_id=cmd_id,
                capability_id=cap_id,
                trust_level=TrustLevel.MEDIUM,
            ),
        )
        permission_result = await self._permission_manager.check_permission(permission_request)

        # Step 4: Handle denial
        if not permission_result.granted:
            reason = permission_result.denial_reason or "Permission denied by Security Kernel."
            self._logger.warning(
                "Execution denied by security kernel.",
                command_id=cmd_id,
                capability_id=cap_id,
                reason=reason,
            )
            await self._event_bus.publish(
                ExecutionDenied(
                    payload={"command_id": cmd_id, "capability_id": cap_id, "reason": reason},
                    source="ExecutionService",
                    command_id=cmd_id,
                    capability_id=cap_id,
                    denial_reason=reason,
                )
            )
            return ExecutionOutcome(
                command_id=cmd_id,
                capability_id=cap_id,
                status=ExecutionOutcomeStatus.DENIED,
                denial_reason=reason,
            )

        # Step 5: Authorization confirmed
        await self._event_bus.publish(
            ExecutionAuthorized(
                payload={"command_id": cmd_id, "capability_id": cap_id},
                source="ExecutionService",
                command_id=cmd_id,
                capability_id=cap_id,
            )
        )

        # Step 6–8: Dispatch to Runtime
        try:
            execution_request = ExecutionRequest(
                execution_id=cmd_id,
                capability_id=cap_id,
                arguments=dict(command.arguments),
                metadata=dict(command.metadata),
            )

            capability = self._dispatcher.dispatch(execution_request, self._registry)

            await self._event_bus.publish(
                ExecutionDispatched(
                    payload={"command_id": cmd_id, "capability_id": cap_id},
                    source="ExecutionService",
                    command_id=cmd_id,
                    capability_id=cap_id,
                )
            )

            from core.runtime.models import ExecutionContext
            context = ExecutionContext(
                request=execution_request,
                capability_metadata=capability.metadata,
            )
            result_data = await self._executor.execute(capability, context)

        except Exception as exc:
            error_msg = f"Runtime execution failed: {exc}"
            self._logger.error(error_msg, command_id=cmd_id, capability_id=cap_id)
            await self._event_bus.publish(
                ExecutionFailed(
                    payload={"command_id": cmd_id, "capability_id": cap_id, "error": error_msg},
                    source="ExecutionService",
                    command_id=cmd_id,
                    capability_id=cap_id,
                    error=error_msg,
                )
            )
            return ExecutionOutcome(
                command_id=cmd_id,
                capability_id=cap_id,
                status=ExecutionOutcomeStatus.FAILED,
                error=error_msg,
            )

        # Step 9: Success
        await self._event_bus.publish(
            ExecutionSucceeded(
                payload={"command_id": cmd_id, "capability_id": cap_id},
                source="ExecutionService",
                command_id=cmd_id,
                capability_id=cap_id,
                result_data=result_data,
            )
        )

        return ExecutionOutcome(
            command_id=cmd_id,
            capability_id=cap_id,
            status=ExecutionOutcomeStatus.SUCCEEDED,
            result_data=result_data,
        )
