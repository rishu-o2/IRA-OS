import uuid
from typing import Optional

from core.events import EventBus
from core.logging import Logger
from core.runtime.interfaces import CapabilityRegistry, Dispatcher, Executor
from core.runtime.models import ExecutionRequest
from core.security.contracts import PermissionManager
from core.security.models import PermissionRequest, SecurityContext, TrustLevel

from .contracts import ExecutionService, ExecutionType, ExecutionClassifier, ProtectedDispatcher
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


class DefaultExecutionClassifier(ExecutionClassifier):
    """
    Classifies a command as either READ or MUTATION based on Capability registry.
    """
    def __init__(self, registry: CapabilityRegistry) -> None:
        self._registry = registry

    def classify(self, command: ExecutionCommand) -> ExecutionType:
        try:
            capability = self._registry.lookup(command.capability_id)
        except Exception:
            # If not found, we return READ so it fails downstream cleanly in runtime/security
            return ExecutionType.READ
            
        if capability and hasattr(capability, "metadata"):
            mutation_meta = getattr(capability.metadata, "mutation", None)
            if mutation_meta and getattr(mutation_meta, "is_mutation", False):
                return ExecutionType.MUTATION
        return ExecutionType.READ


class DefaultProtectedDispatcher(ProtectedDispatcher):
    """
    The protected inner core of the Execution pipeline.
    This component enforcing Security before dispatching to Runtime.
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

    async def dispatch(self, command: ExecutionCommand) -> ExecutionOutcome:
        cmd_id = command.command_id
        cap_id = command.capability_id

        # Security authorization
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

        # Handle denial
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
                    source="ProtectedDispatcher",
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

        # Authorization confirmed
        await self._event_bus.publish(
            ExecutionAuthorized(
                payload={"command_id": cmd_id, "capability_id": cap_id},
                source="ProtectedDispatcher",
                command_id=cmd_id,
                capability_id=cap_id,
            )
        )

        # Dispatch to Runtime
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
                    source="ProtectedDispatcher",
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
                    source="ProtectedDispatcher",
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

        # Success
        await self._event_bus.publish(
            ExecutionSucceeded(
                payload={"command_id": cmd_id, "capability_id": cap_id},
                source="ProtectedDispatcher",
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


class DefaultExecutionService(ExecutionService):
    """
    The canonical implementation of the ExecutionService kernel.
    Serves as the ONLY public entry point for capability execution.
    It determines the command type via ExecutionClassifier and routes
    mutations to the MutationManager, ensuring the mutation lifecycle
    cannot be bypassed.
    """

    def __init__(
        self,
        classifier: ExecutionClassifier,
        protected_dispatcher: ProtectedDispatcher,
        mutation_manager: Any, # Typed as Any to avoid circular import if needed
        event_bus: EventBus,
        logger: Logger,
    ) -> None:
        self._classifier = classifier
        self._protected_dispatcher = protected_dispatcher
        self._mutation_manager = mutation_manager
        self._event_bus = event_bus
        self._logger = logger

    async def execute(self, command: ExecutionCommand) -> ExecutionOutcome:
        if not command or not command.command_id or not command.capability_id:
            raise ExecutionValidationError("ExecutionCommand must have a command_id and capability_id.")

        # Step 1: Publish requested event
        await self._event_bus.publish(
            ExecutionRequested(
                payload={"command_id": command.command_id, "capability_id": command.capability_id},
                source="ExecutionService",
                command_id=command.command_id,
                capability_id=command.capability_id,
            )
        )

        # Step 2: Classify Execution
        exec_type = self._classifier.classify(command)

        # Step 3: Route Execution
        if exec_type == ExecutionType.MUTATION:
            if not self._mutation_manager:
                raise ExecutionRuntimeError("MutationManager is required for MUTATION execution.")
            self._logger.info("Routing command to MutationManager.", command_id=command.command_id)
            return await self._mutation_manager.process_mutation(command, self._protected_dispatcher)
        else:
            self._logger.info("Routing command to ProtectedDispatcher.", command_id=command.command_id)
            return await self._protected_dispatcher.dispatch(command)
