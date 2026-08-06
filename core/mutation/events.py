from dataclasses import dataclass
from typing import Any, Mapping, Optional

from core.events import Event
from .models import AuditRecord, MutationContext


@dataclass(frozen=True, kw_only=True)
class MutationRequested(Event):
    context: MutationContext
    arguments: Mapping[str, Any]


@dataclass(frozen=True, kw_only=True)
class MutationConfirmed(Event):
    context: MutationContext


@dataclass(frozen=True, kw_only=True)
class MutationRejected(Event):
    context: MutationContext
    reason: str


@dataclass(frozen=True, kw_only=True)
class MutationStarted(Event):
    context: MutationContext


@dataclass(frozen=True, kw_only=True)
class MutationCompleted(Event):
    context: MutationContext
    result_data: Optional[Any] = None


@dataclass(frozen=True, kw_only=True)
class MutationRolledBack(Event):
    context: MutationContext
    reason: str


@dataclass(frozen=True, kw_only=True)
class RollbackFailed(Event):
    context: MutationContext
    error: str


@dataclass(frozen=True, kw_only=True)
class AuditRecorded(Event):
    context: MutationContext
    audit_record: AuditRecord
