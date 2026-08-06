from abc import ABC, abstractmethod
from typing import Any, Mapping

from core.execution.models import ExecutionCommand, ExecutionOutcome
from core.runtime.interfaces import Capability
from .models import AuditRecord, ConfirmationLevel, MutationContext, MutationState


class MutationManager(ABC):
    """
    Coordinates the mutation lifecycle.
    
    The MutationManager does NOT execute capabilities. It wraps the execution
    (provided by the ExecutionService) in the mutation lifecycle:
    Confirmation -> Execution -> Audit -> Rollback (if failed).
    """

    @abstractmethod
    async def process_mutation(self, command: ExecutionCommand) -> ExecutionOutcome:
        """
        Process a mutation command through the full lifecycle.
        """
        pass


class ConfirmationProvider(ABC):
    """
    Pluggable contract for confirming mutations.
    Implementations could be CLI, Android UI, Web, etc.
    """

    @abstractmethod
    def supports(self, level: ConfirmationLevel) -> bool:
        """Returns True if this provider can handle the given confirmation level."""
        pass

    @abstractmethod
    async def request_confirmation(self, context: MutationContext, level: ConfirmationLevel) -> bool:
        """
        Request confirmation from the user/owner.
        Returns True if confirmed, False if rejected or timed out.
        """
        pass


class AuditSink(ABC):
    """
    Pluggable destination for audit records.
    Multiple sinks can be registered (e.g., Local SQLite, Cloud, etc.).
    """

    @abstractmethod
    async def record(self, record: AuditRecord) -> None:
        """Persist the audit record to the sink."""
        pass


class MutatingCapability(Capability):
    """
    Contract for any capability that changes the real world.
    Every mutation capability must implement this interface to support
    the mutation lifecycle (including rollback if applicable).
    """

    @abstractmethod
    def supports_rollback(self, arguments: Mapping[str, Any]) -> bool:
        """
        Returns True if this specific mutation (with given args) can be rolled back.
        """
        pass

    @abstractmethod
    async def rollback(self, arguments: Mapping[str, Any], original_result: Any) -> None:
        """
        Attempt to undo the mutation.
        Raises RollbackError if it fails.
        """
        pass


class MutationPolicy(ABC):
    """
    Evaluates whether a mutation should proceed, requires confirmation, or is rejected.
    """

    @abstractmethod
    def evaluate(self, command: ExecutionCommand) -> MutationState:
        """
        Returns the initial state:
        - EXECUTING (Execute immediately)
        - WAITING_CONFIRMATION (Require confirmation)
        - REJECTED (Reject)
        """
        pass
