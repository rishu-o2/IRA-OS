from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping

from core.identity import Identity

from .exceptions import BrainValidationError


def _immutable_mapping(value: Mapping[str, Any] | None) -> Mapping[str, Any]:
    if value is None:
        return MappingProxyType({})
    if not isinstance(value, Mapping):
        raise BrainValidationError("Metadata must be a mapping.")
    return MappingProxyType(dict(value))


def _immutable_string_tuple(value: Any, field_name: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    try:
        return tuple(str(item) for item in value)
    except TypeError as exc:
        raise BrainValidationError(f"{field_name} must be a string or iterable of strings.") from exc


class BrainDecisionType(str, Enum):
    PLAN_READY = "PLAN_READY"
    FAILED = "FAILED"


@dataclass(frozen=True)
class ConversationTurn:
    role: str
    content: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))

    def __post_init__(self) -> None:
        if not self.role:
            raise BrainValidationError("ConversationTurn.role must not be empty.")
        object.__setattr__(self, "content", str(self.content))
        object.__setattr__(self, "metadata", _immutable_mapping(self.metadata))


@dataclass(frozen=True)
class BrainRequest:
    request_id: str
    user_id: str
    payload: Any
    metadata: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        if not self.request_id:
            raise BrainValidationError("BrainRequest.request_id must not be empty.")
        if not self.user_id:
            raise BrainValidationError("BrainRequest.user_id must not be empty.")
        if self.payload is None:
            raise BrainValidationError("BrainRequest.payload must not be None.")
        object.__setattr__(self, "metadata", _immutable_mapping(self.metadata))


@dataclass(frozen=True)
class BrainAnalysis:
    normalized_text: str
    intent: str
    memory_query_text: str
    memory_tags: tuple[str, ...] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))

    def __post_init__(self) -> None:
        if not self.normalized_text:
            raise BrainValidationError("BrainAnalysis.normalized_text must not be empty.")
        if not self.intent:
            raise BrainValidationError("BrainAnalysis.intent must not be empty.")
        object.__setattr__(self, "memory_tags", _immutable_string_tuple(self.memory_tags, "BrainAnalysis.memory_tags"))
        object.__setattr__(self, "metadata", _immutable_mapping(self.metadata))


@dataclass(frozen=True)
class BrainIdentityContext:
    identity_id: str
    username: str
    display_name: str
    active: bool
    roles: tuple[str, ...] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))

    @classmethod
    def from_identity(cls, identity: Identity) -> "BrainIdentityContext":
        return cls(
            identity_id=identity.id,
            username=identity.username,
            display_name=identity.display_name,
            active=identity.active,
            roles=tuple(getattr(role, "name", str(role)) for role in identity.roles),
            metadata=identity.metadata,
        )

    def __post_init__(self) -> None:
        if not self.identity_id:
            raise BrainValidationError("BrainIdentityContext.identity_id must not be empty.")
        object.__setattr__(self, "roles", tuple(self.roles))
        object.__setattr__(self, "metadata", _immutable_mapping(self.metadata))


@dataclass(frozen=True)
class BrainPlannerInput:
    goal_id: str
    request_id: str
    user_id: str
    normalized_request: str
    intent: str
    memory_ids: tuple[str, ...] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))

    def __post_init__(self) -> None:
        if not self.goal_id:
            raise BrainValidationError("BrainPlannerInput.goal_id must not be empty.")
        object.__setattr__(self, "memory_ids", _immutable_string_tuple(self.memory_ids, "BrainPlannerInput.memory_ids"))
        object.__setattr__(self, "metadata", _immutable_mapping(self.metadata))


@dataclass(frozen=True)
class BrainPlanSummary:
    goal_id: str
    task_ids: tuple[str, ...]
    estimated_steps: int
    created_at: datetime

    def __post_init__(self) -> None:
        if not self.goal_id:
            raise BrainValidationError("BrainPlanSummary.goal_id must not be empty.")
        if self.estimated_steps < 0:
            raise BrainValidationError("BrainPlanSummary.estimated_steps must not be negative.")
        object.__setattr__(self, "task_ids", _immutable_string_tuple(self.task_ids, "BrainPlanSummary.task_ids"))


@dataclass(frozen=True)
class BrainDecision:
    request_id: str
    user_id: str
    decision_type: BrainDecisionType
    plan_summary: BrainPlanSummary
    memory_count: int
    metadata: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))

    def __post_init__(self) -> None:
        if self.memory_count < 0:
            raise BrainValidationError("BrainDecision.memory_count must not be negative.")
        object.__setattr__(self, "metadata", _immutable_mapping(self.metadata))


@dataclass(frozen=True)
class BrainResult:
    success: bool
    decision: BrainDecision | None = None
    error: str | None = None
    request_id: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        if self.success and self.decision is None:
            raise BrainValidationError("Successful BrainResult requires a decision.")
        if not self.success and not self.error:
            raise BrainValidationError("Failed BrainResult requires an error.")
