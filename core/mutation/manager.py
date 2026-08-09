import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Coroutine, Mapping

from core.events import EventBus
from core.execution.models import ExecutionCommand, ExecutionOutcome, ExecutionOutcomeStatus
from core.logging import Logger
from core.runtime.interfaces import CapabilityRegistry

from .audit import AuditManager
from .confirmation import ConfirmationManager
from .contracts import MutatingCapability, MutationManager
from .events import (
    AuditRecorded,
    MutationCompleted,
    MutationConfirmed,
    MutationRejected,
    MutationRequested,
    MutationRolledBack,
    MutationStarted,
    RollbackFailed,
)
from .exceptions import MutationError, MutationRejectedError, RollbackError
from .models import AuditRecord, ConfirmationLevel, MutationContext, MutationMetadata, MutationState


class DefaultMutationManager(MutationManager):
    """
    Coordinates the canonical mutation lifecycle.
    
    Responsibilities:
    1. Check capability metadata.
    2. Coordinate confirmation (if required).
    3. Invoke the execute_delegate supplied by ExecutionService (Security → Runtime → Capability).
    4. Coordinate audit persistence.
    5. Coordinate rollback (if execution fails or requires undo).

    This class is NOT public. It is owned and invoked solely by DefaultExecutionService.
    It has zero knowledge of Runtime, Security, or any platform bridge.
    """

    def __init__(
        self,
        capability_registry: CapabilityRegistry,
        confirmation_manager: ConfirmationManager,
        audit_manager: AuditManager,
        event_bus: EventBus,
        logger: Logger,
    ) -> None:
        self._registry = capability_registry
        self._confirmation_manager = confirmation_manager
        self._audit_manager = audit_manager
        self._event_bus = event_bus
        self._logger = logger

    async def process_mutation(
        self,
        command: ExecutionCommand,
        execute_delegate: Callable[[ExecutionCommand], Coroutine[Any, Any, ExecutionOutcome]],
    ) -> ExecutionOutcome:
        """
        Execute the full mutation lifecycle.
        
        execute_delegate: callable supplied by ExecutionService that performs
        Security → Runtime → Capability. MutationManager never calls these directly.
        """
        mutation_id = str(uuid.uuid4())
        context = MutationContext(
            mutation_id=mutation_id,
            workflow_id=command.metadata.get("workflow_id"),
            execution_id=command.command_id,
            capability_id=command.capability_id,
            user_id=command.metadata.get("user_id"),
        )
        started_at = datetime.now(timezone.utc)

        # 1. Resolve capability to inspect metadata
        try:
            capability = self._registry.lookup(command.capability_id)
        except Exception as e:
            self._logger.error("Capability not found in registry.", capability_id=command.capability_id)
            return self._build_outcome(command, ExecutionOutcomeStatus.FAILED, error="Capability not found.")
            
        # We assume capability.metadata has mutation metadata. 
        # (This will be properly typed when we integrate it into Runtime models)
        mutation_meta = getattr(capability.metadata, "mutation", MutationMetadata())
        
        # 2. Publish Requested Event
        await self._event_bus.publish(
            MutationRequested(
                payload={"mutation_id": mutation_id, "capability_id": command.capability_id},
                source="MutationManager",
                context=context,
                arguments=command.arguments,
            )
        )

        # 3. Handle Confirmation
        if mutation_meta.confirmation_level != ConfirmationLevel.NONE:
            confirmed = await self._confirmation_manager.request_confirmation(context, mutation_meta.confirmation_level)
            if not confirmed:
                reason = f"Confirmation denied for level {mutation_meta.confirmation_level.value}"
                await self._event_bus.publish(
                    MutationRejected(
                        payload={"mutation_id": mutation_id, "reason": reason},
                        source="MutationManager",
                        context=context,
                        reason=reason,
                    )
                )
                
                if mutation_meta.audit_required:
                    await self._record_audit(
                        context, command, MutationState.REJECTED, started_at, error=reason
                    )
                    
                return self._build_outcome(command, ExecutionOutcomeStatus.DENIED, denial_reason=reason)
            
            await self._event_bus.publish(
                MutationConfirmed(
                    payload={"mutation_id": mutation_id},
                    source="MutationManager",
                    context=context,
                )
            )

        # 4. Execute
        await self._event_bus.publish(
            MutationStarted(
                payload={"mutation_id": mutation_id},
                source="MutationManager",
                context=context,
            )
        )

        outcome = await execute_delegate(command)

        # 5. Handle Failure and Rollback
        if outcome.failed and mutation_meta.supports_rollback:
            if isinstance(capability, MutatingCapability):
                if capability.supports_rollback(command.arguments):
                    try:
                        self._logger.info("Execution failed, attempting rollback.", mutation_id=mutation_id)
                        await capability.rollback(command.arguments, original_result=outcome.result_data)
                        
                        await self._event_bus.publish(
                            MutationRolledBack(
                                payload={"mutation_id": mutation_id},
                                source="MutationManager",
                                context=context,
                                reason=outcome.error or "Execution failed",
                            )
                        )
                    except Exception as e:
                        error_msg = f"Rollback failed: {e}"
                        self._logger.error(error_msg, mutation_id=mutation_id)
                        await self._event_bus.publish(
                            RollbackFailed(
                                payload={"mutation_id": mutation_id, "error": error_msg},
                                source="MutationManager",
                                context=context,
                                error=error_msg,
                            )
                        )
                        outcome = self._build_outcome(command, ExecutionOutcomeStatus.FAILED, error=f"{outcome.error} | {error_msg}")

        # 6. Audit
        if mutation_meta.audit_required:
            state = self._map_outcome_to_state(outcome)
            await self._record_audit(
                context, command, state, started_at, result=outcome.result_data, error=outcome.error or outcome.denial_reason
            )

        # 7. Complete
        if outcome.succeeded:
            await self._event_bus.publish(
                MutationCompleted(
                    payload={"mutation_id": mutation_id},
                    source="MutationManager",
                    context=context,
                    result_data=outcome.result_data,
                )
            )

        return outcome

    async def _record_audit(
        self,
        context: MutationContext,
        command: ExecutionCommand,
        status: MutationState,
        started_at: datetime,
        result: Any = None,
        error: str = None,
    ) -> None:
        audit_id = str(uuid.uuid4())
        record = AuditRecord(
            audit_id=audit_id,
            mutation_id=context.mutation_id,
            capability_id=context.capability_id,
            action="execute",
            arguments=command.arguments,
            status=status,
            started_at=started_at,
            completed_at=datetime.now(timezone.utc),
            result_data=result,
            error=error,
            workflow_id=context.workflow_id,
            user_id=context.user_id,
        )
        try:
            await self._audit_manager.record(record)
            await self._event_bus.publish(
                AuditRecorded(
                    payload={"audit_id": audit_id, "mutation_id": context.mutation_id},
                    source="MutationManager",
                    context=context,
                    audit_record=record,
                )
            )
        except Exception as e:
            self._logger.error(f"Failed to record audit: {e}", mutation_id=context.mutation_id)

    def _map_outcome_to_state(self, outcome: ExecutionOutcome) -> MutationState:
        if outcome.succeeded:
            return MutationState.COMPLETED
        if outcome.denied:
            return MutationState.REJECTED
        return MutationState.FAILED

    def _build_outcome(self, command: ExecutionCommand, status: ExecutionOutcomeStatus, result_data: Any = None, denial_reason: str = None, error: str = None) -> ExecutionOutcome:
        return ExecutionOutcome(
            command_id=command.command_id,
            capability_id=command.capability_id,
            status=status,
            result_data=result_data,
            denial_reason=denial_reason,
            error=error,
        )
