"""
core.execution — Execution Service Kernel

The single authoritative entry point for all platform capability execution.
No subsystem other than ExecutionService may call RuntimeManager directly.

Canonical pipeline:
    Brain → Planner → Workflow → ExecutionService → Security → Runtime → Platform
"""

from .contracts import ExecutionService
from .exceptions import (
    ExecutionServiceError,
    ExecutionPermissionDeniedError,
    ExecutionRuntimeError,
    ExecutionValidationError,
)
from .events import (
    ExecutionRequested,
    ExecutionAuthorized,
    ExecutionDispatched,
    ExecutionSucceeded,
    ExecutionDenied,
    ExecutionFailed,
)
from .models import (
    ExecutionCommand,
    ExecutionOutcome,
    ExecutionOutcomeStatus,
)
from .execution_module import ExecutionModule

__all__ = [
    # Public contracts
    "ExecutionService",
    "ExecutionModule",
    # Models
    "ExecutionCommand",
    "ExecutionOutcome",
    "ExecutionOutcomeStatus",
    # Events
    "ExecutionRequested",
    "ExecutionAuthorized",
    "ExecutionDispatched",
    "ExecutionSucceeded",
    "ExecutionDenied",
    "ExecutionFailed",
    # Exceptions
    "ExecutionServiceError",
    "ExecutionPermissionDeniedError",
    "ExecutionRuntimeError",
    "ExecutionValidationError",
]
