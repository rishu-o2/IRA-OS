from core.execution.models import ExecutionCommand
from .contracts import MutationPolicy
from .models import MutationState


class ExecuteImmediatelyPolicy(MutationPolicy):
    """
    Policy that allows the mutation to proceed without confirmation.
    """
    def evaluate(self, command: ExecutionCommand) -> MutationState:
        return MutationState.EXECUTING


class RequireConfirmationPolicy(MutationPolicy):
    """
    Policy that halts the mutation to request confirmation.
    """
    def evaluate(self, command: ExecutionCommand) -> MutationState:
        return MutationState.WAITING_CONFIRMATION


class RejectPolicy(MutationPolicy):
    """
    Policy that immediately rejects the mutation.
    """
    def evaluate(self, command: ExecutionCommand) -> MutationState:
        return MutationState.REJECTED


class CapabilityDrivenPolicy(MutationPolicy):
    """
    Policy that evaluates the capability's own metadata (confirmation_level).
    (This requires a registry lookup to get the capability metadata, which will be wired in the Manager).
    """
    pass 
