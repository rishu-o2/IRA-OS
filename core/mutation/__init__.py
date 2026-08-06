"""
core.mutation — Mutation Lifecycle Framework

Coordinates the lifecycle of state-changing capabilities across IRA OS.
Handles confirmations, execution dispatching, auditing, and rollbacks.
"""

from .contracts import (
    AuditSink,
    ConfirmationProvider,
    MutatingCapability,
    MutationManager,
    MutationPolicy,
)
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
from .exceptions import (
    AuditError,
    ConfirmationRequired,
    MutationError,
    MutationRejectedError,
    RollbackError,
)
from .models import (
    AuditRecord,
    ConfirmationLevel,
    MutationContext,
    MutationMetadata,
    MutationState,
)
from .mutation_module import MutationModule

__all__ = [
    # Contracts
    "MutationManager",
    "ConfirmationProvider",
    "AuditSink",
    "MutatingCapability",
    "MutationPolicy",
    # Models
    "MutationState",
    "ConfirmationLevel",
    "MutationMetadata",
    "MutationContext",
    "AuditRecord",
    # Events
    "MutationRequested",
    "MutationConfirmed",
    "MutationRejected",
    "MutationStarted",
    "MutationCompleted",
    "MutationRolledBack",
    "RollbackFailed",
    "AuditRecorded",
    # Exceptions
    "MutationError",
    "ConfirmationRequired",
    "MutationRejectedError",
    "RollbackError",
    "AuditError",
    # DI
    "MutationModule",
]
