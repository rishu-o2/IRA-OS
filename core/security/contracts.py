from abc import ABC, abstractmethod
from typing import Optional, Tuple

from core.lifecycle.models import ComponentHealth

from .models import (
    PermissionDecision,
    PermissionPolicy,
    PermissionRequest,
    PermissionRequirement,
    PermissionResult,
    SecurityContext,
)


class PermissionValidator(ABC):
    """Validates the shape and semantics of a PermissionRequest."""

    @abstractmethod
    def validate(self, request: PermissionRequest) -> None:
        """Raises PermissionValidationError if the request is invalid."""
        pass


class PolicyEvaluator(ABC):
    """Evaluates applicable policies for a permission request."""

    @abstractmethod
    def load_policy(self, policy: PermissionPolicy) -> None:
        """Registers a policy into the evaluator."""
        pass

    @abstractmethod
    def evaluate(self, request: PermissionRequest) -> PermissionDecision:
        """Returns a PermissionDecision based on loaded policies."""
        pass


class PermissionAuthorizer(ABC):
    """Converts a PermissionDecision into a final PermissionResult."""

    @abstractmethod
    def authorize(self, decision: PermissionDecision) -> PermissionResult:
        """Grants or denies execution based on the decision."""
        pass


class PermissionManager(ABC):
    """
    Abstract contract for the Permission & Security Kernel Manager.
    Lifecycle-aware orchestrator of the full canonical pipeline.
    """

    @abstractmethod
    async def check_permission(self, request: PermissionRequest) -> PermissionResult:
        """
        Execute the canonical permission pipeline:
        Validate -> Load Policy -> Evaluate -> Authorize -> Publish -> Return.
        """
        pass

    @abstractmethod
    async def start(self) -> None:
        """Start the security kernel. Must be idempotent."""
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        """Shut down the security kernel. Must be idempotent."""
        pass

    @abstractmethod
    async def health_check(self) -> ComponentHealth:
        """Return the current health state of the security kernel."""
        pass
