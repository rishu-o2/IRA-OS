from abc import ABC, abstractmethod
from enum import Enum

from .models import ExecutionCommand, ExecutionOutcome

class ExecutionType(Enum):
    READ = "READ"
    MUTATION = "MUTATION"

class ExecutionClassifier(ABC):
    """
    Classifies a command as either READ or MUTATION.
    Prevents ExecutionService from coupling to capability metadata details.
    """
    @abstractmethod
    def classify(self, command: ExecutionCommand) -> ExecutionType:
        pass

class ProtectedDispatcher(ABC):
    """
    Contract for protected dispatch into the Security and Runtime layers.
    Used by internal orchestrators (like MutationManager) to trigger
    actual execution once lifecycle rules are satisfied.
    """
    @abstractmethod
    async def dispatch(self, command: ExecutionCommand) -> ExecutionOutcome:
        pass

class ExecutionService(ABC):
    """
    Abstract contract for the Execution Service.

    The ExecutionService is the single authoritative entry point
    for all platform capability execution in IRA OS.

    No subsystem other than ExecutionService may invoke the Runtime directly.

    Pipeline enforced by implementations:
        Workflow → ExecutionService → Security → Runtime → Platform

    The ExecutionService is:
      - Platform-agnostic: it never imports Android, Windows, or any platform code.
      - Security-enforcing: it always passes through the PermissionKernel.
      - Observable: it publishes events for every stage of execution.
    """

    @abstractmethod
    async def execute(self, command: ExecutionCommand) -> ExecutionOutcome:
        """
        Execute a capability command through the full security and runtime pipeline.

        This method must:
          1. Validate the command.
          2. Request security authorization from the PermissionKernel.
          3. If denied, return a denied ExecutionOutcome immediately.
          4. Dispatch the authorized command to the RuntimeManager.
          5. Return a normalized ExecutionOutcome.

        Raises:
            ExecutionValidationError: if the command is structurally invalid.
        """
        pass
