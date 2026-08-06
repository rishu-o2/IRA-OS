from abc import ABC, abstractmethod

from .models import ExecutionCommand, ExecutionOutcome


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
